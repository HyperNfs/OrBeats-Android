package dev.orbeats.android;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

public final class CoreTest {
    interface Checked { void run() throws Exception; }
    static int checked;
    static void check(boolean ok) { checked++; if (!ok) throw new AssertionError("Check " + checked); }
    static void refused(Checked action) throws Exception {
        checked++;
        try { action.run(); } catch (IOException expected) { return; }
        throw new AssertionError("Unsafe input accepted at check " + checked);
    }
    static BufferedReader reader(String value) { return new BufferedReader(new StringReader(value)); }
    static File zip(Path dir, String[] names, byte[][] contents) throws IOException {
        File f = File.createTempFile("map", ".zip", dir.toFile());
        try (ZipOutputStream out = new ZipOutputStream(new FileOutputStream(f))) {
            for (int i=0;i<names.length;i++) {
                ZipEntry e = new ZipEntry(names[i]);
                e.setMethod(ZipEntry.STORED);
                CRC32 crc = new CRC32(); crc.update(contents[i]);
                e.setSize(contents[i].length); e.setCrc(crc.getValue());
                out.putNextEntry(e); out.write(contents[i]); out.closeEntry();
            }
        }
        return f;
    }
    static byte[] bytes(String value) { return value.getBytes(StandardCharsets.UTF_8); }
    public static void main(String[] args) throws Exception {
        for (String host : new String[]{"api.beatsaver.com", "cdn.beatsaver.com", "r2cdn.beatsaver.com", "cfcdn.beatsaver.com"})
            check(Core.trustedUrl("https://"+host+"/x").getHost().equals(host));
        for (String url : new String[]{"http://api.beatsaver.com/a", "https://api.beatsaver.com.evil/a", "https://evil@api.beatsaver.com/a", "https://127.0.0.1/a", "file:///etc/passwd", "https://api.beatsaver.com:2121/a", "https://api.beatsaver.com/a#x"})
            refused(()->Core.trustedUrl(url));
        check(Core.scorePercent(0.829)==82);
        check(Core.scorePercent(0.887)==88);
        check(Core.scorePercent(0.918)==91);
        check(Core.scorePercent(0.864)==86);
        check(Core.scorePercent(0.8386)==83);
        check(Core.scorePercent(0.29)==29);
        check(Core.scorePercent(0.58)==58);
        check(Core.scorePercent(0)==0 && Core.scorePercent(1)==100);
        check(Core.scorePercent(0.99999)==99);
        for(double score:new double[]{Double.NaN,Double.POSITIVE_INFINITY,Double.NEGATIVE_INFINITY,-0.01,1.01})check(Core.scorePercent(score)==-1);
        check(Core.validId("abcd123"));
        for (String id : new String[]{"../x", "", "/tmp/a", "x", "a/b", "abcdefghijklmnopq", "a1234567890123456a"}) check(!Core.validId(id));
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        check(Core.copy(new ByteArrayInputStream(bytes("abc")),out,3)==3);
        check(Arrays.equals(out.toByteArray(),bytes("abc")));
        refused(()->Core.copy(new ByteArrayInputStream(bytes("abcd")),new ByteArrayOutputStream(),3));
        refused(()->Core.copy(new ByteArrayInputStream(bytes("a")),new ByteArrayOutputStream(),0));
        Thread.currentThread().interrupt();
        try { refused(()->Core.copy(new ByteArrayInputStream(bytes("a")),new ByteArrayOutputStream(),3)); }
        finally { Thread.interrupted(); }
        check(Core.privateAddress(" 192.168.001.195 ").equals("192.168.1.195"));
        check(Core.privateAddress("10.0.0.5").equals("10.0.0.5"));
        check(Core.privateAddress("172.16.0.1").equals("172.16.0.1"));
        check(Core.privateAddress("172.31.255.1").equals("172.31.255.1"));
        for (String ip : new String[]{"8.8.8.8", "127.0.0.1", "192.168.1.256", "192.168.1", "172.32.0.1", "172.15.1.1", "localhost", "192.168.1.2\r\nUSER x", "192.168.1.-1"}) refused(()->Core.privateAddress(ip));
        check(Core.port("2121")==2121); check(Core.port("65535")==65535);
        for (String port : new String[]{"0","65536","x","-1","2147483648"}) refused(()->Core.port(port));
        check(Core.reply(reader("220 ready\r\n"))==220);
        check(Core.reply(reader("220-first\r\nhello\r\n220 ready\r\n"))==220);
        check(Core.reply(reader("331 password\r\n"))==331);
        for (String response : new String[]{"", "hello\r\n", "220", "220Xwrong\n", "220-unclosed\n"}) refused(()->Core.reply(reader(response)));
        refused(()->Core.reply(reader("220 "+String.join("",Collections.nCopies(1100,"a"))+"\n")));
        refused(()->Core.reply(reader("220-first\n"+String.join("",Collections.nCopies(65,"x\n")))));
        Path tmp=Files.createTempDirectory("orbeats-core-");
        try {
            File pending=tmp.resolve(".pending-"+UUID.randomUUID()).toFile(),kept=tmp.resolve("abcd").toFile();
            check(pending.mkdir() && kept.mkdir());
            Files.write(new File(pending,"map.zip").toPath(),bytes("partial"));
            Files.write(new File(pending,"map.json").toPath(),bytes("{}"));
            File saved=new File(kept,"map.zip");Files.write(saved.toPath(),bytes("saved"));
            Core.cleanupPending(tmp.toFile());
            check(!pending.exists());check(saved.isFile());
            saved.delete();kept.delete();
            Core.validateZip(zip(tmp,new String[]{"Info.dat","song.ogg"},new byte[][]{bytes("{}"),bytes("audio")}));checked++;
            Core.validateZip(zip(tmp,new String[]{"folder/info.dat"},new byte[][]{bytes("{}")}));checked++;
            refused(()->Core.validateZip(zip(tmp,new String[]{"song.ogg"},new byte[][]{bytes("audio")})));
            refused(()->Core.validateZip(zip(tmp,new String[]{"Info.dat"},new byte[][]{new byte[0]})));
            for (String name : new String[]{"../Info.dat","/Info.dat","a/../../Info.dat","C:/Info.dat","..\\Info.dat"})
                refused(()->Core.validateZip(zip(tmp,new String[]{name},new byte[][]{bytes("{}")})));
            refused(()->Core.validateZip(zip(tmp,new String[]{"Info.dat","b/info.dat"},new byte[][]{bytes("{}"),bytes("{}")})));
            refused(()->Core.validateZip(zip(tmp,new String[]{"Info.dat"},new byte[][]{new byte[2*1024*1024+1]})));
            File corrupt=zip(tmp,new String[]{"Info.dat"},new byte[][]{bytes("unique_crc_payload")});
            byte[] data=Files.readAllBytes(corrupt.toPath());
            byte[] marker=bytes("unique_crc_payload");
            for(int i=0;i<=data.length-marker.length;i++){
                boolean match=true;for(int j=0;j<marker.length;j++)if(data[i+j]!=marker[j])match=false;
                if(match){data[i]='X';break;}
            }
            Files.write(corrupt.toPath(),data);
            refused(()->Core.validateZip(corrupt));
            File notZip=tmp.resolve("not.zip").toFile();Files.write(notZip.toPath(),bytes("not a zip"));refused(()->Core.validateZip(notZip));
        } finally { File[] files=tmp.toFile().listFiles();if(files!=null)for(File f:files)f.delete();tmp.toFile().delete(); }
        if (args.length>0 && args[0].equals("--live")) {
            String live=new String(Core.bytes("https://api.beatsaver.com/search/text/0?q=&sortOrder=Curated",2L*1024*1024),StandardCharsets.UTF_8);
            check(live.contains("\"docs\"")&&live.contains("\"downloadURL\""));
            System.out.println("PASS: live BeatSaver HTTPS search");
        }
        // Isolated fake HTTPS headers: no body download, redirects remain allowlisted and bounded.
        URL.setURLStreamHandlerFactory(protocol->protocol.equals("https")?new URLStreamHandler(){
            @Override protected URLConnection openConnection(URL url){return new HttpURLConnection(url){
                public void connect(){} public void disconnect(){} public boolean usingProxy(){return false;}
                public int getResponseCode(){if(!getRequestMethod().equals("HEAD"))throw new AssertionError("Expected HEAD");return url.getPath().equals("/loop")||url.getPath().equals("/redirect")?302:url.getPath().equals("/missing")?404:200;}
                public String getHeaderField(String name){return name.equals("Location")?(url.getPath().equals("/loop")?"/loop":"http://unsafe.test/file"):null;}
                public long getContentLengthLong(){return url.getPath().equals("/large")?Core.MAX_ZIP+1:url.getPath().equals("/unknown")?-1:8256660;}
                public InputStream getInputStream(){throw new AssertionError("Size query read a download body");}
            };}
        }:null);
        check(Core.downloadSize("https://r2cdn.beatsaver.com/ok")==8256660);
        check(Core.downloadSize("https://r2cdn.beatsaver.com/unknown")==-1);
        for(String path:new String[]{"large","redirect","loop","missing"})refused(()->Core.downloadSize("https://r2cdn.beatsaver.com/"+path));
        System.out.println("PASS: "+checked+" Core boundary/parser/archive/header checks (not Android UI execution)");
    }
}
