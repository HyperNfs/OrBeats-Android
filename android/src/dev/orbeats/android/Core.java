package dev.orbeats.android;

import java.io.*;
import java.net.*;
import java.util.Locale;
import java.util.zip.*;

/** Platform-independent boundaries shared by the app and host tests. */
final class Core {
    static final long MAX_ZIP = 128L * 1024 * 1024;

    static URL trustedUrl(String raw) throws IOException {
        URL url = new URL(raw);
        String host = url.getHost().toLowerCase(Locale.ROOT);
        if (!"https".equals(url.getProtocol()) || url.getUserInfo() != null || url.getRef() != null ||
            (url.getPort() != -1 && url.getPort() != 443) ||
            !(host.equals("api.beatsaver.com") || host.equals("cdn.beatsaver.com") ||
              host.equals("r2cdn.beatsaver.com") || host.equals("cfcdn.beatsaver.com")))
            throw new IOException("Refused an untrusted BeatSaver URL");
        return url;
    }

    static final class HttpError extends IOException {
        final int status;
        HttpError(int status) { super("BeatSaver returned HTTP " + status); this.status = status; }
    }

    static void fetch(String raw, OutputStream destination, long limit) throws IOException {
        fetch(raw,destination,limit,false);
    }

    static long downloadSize(String raw) throws IOException { return fetch(raw,null,MAX_ZIP,true); }

    private static long fetch(String raw, OutputStream destination, long limit, boolean head) throws IOException {
        URL url = trustedUrl(raw);
        for (int redirects = 0; redirects <= 3; redirects++) {
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            if(head)connection.setRequestMethod("HEAD");
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(30000);
            connection.setInstanceFollowRedirects(false);
            connection.setRequestProperty("User-Agent", "OrBeatsAndroid/0.1.2");
            connection.setRequestProperty("Accept-Encoding", "identity");
            try {
                int status = connection.getResponseCode();
                if (status == 301 || status == 302 || status == 303 || status == 307 || status == 308) {
                    String location = connection.getHeaderField("Location");
                    if (location == null) throw new IOException("Empty redirect");
                    url = trustedUrl(new URL(url, location).toString());
                    continue;
                }
                if (status == 429) throw new IOException("BeatSaver rate limit. Wait a little before retrying.");
                if (status != 200) throw new HttpError(status);
                long length = connection.getContentLengthLong();
                if (length > limit) throw new IOException("Download exceeds the size limit");
                if(head)return length;
                try (InputStream input = connection.getInputStream()) {
                    long copied = copy(input, destination, limit);
                    if (length >= 0 && copied != length) throw new IOException("Incomplete download");
                }
                return length;
            } finally { connection.disconnect(); }
        }
        throw new IOException("Too many redirects");
    }

    static byte[] bytes(String url, long limit) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        fetch(url, output, limit);
        return output.toByteArray();
    }

    static long copy(InputStream input, OutputStream output, long limit) throws IOException {
        byte[] buffer = new byte[32768];
        long count = 0;
        int n;
        while ((n = input.read(buffer)) != -1) {
            if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Cancelled");
            if (n > limit - count) throw new IOException("Content exceeds the size limit");
            output.write(buffer, 0, n); count += n;
        }
        return count;
    }

    static int scorePercent(double score) {
        if (!Double.isFinite(score) || score < 0 || score > 1) return -1;
        // Decimal arithmetic avoids turning exact values such as 0.29 into 28%.
        return java.math.BigDecimal.valueOf(score).movePointRight(2).intValue();
    }

    static boolean validId(String id) { return id != null && id.matches("[a-fA-F0-9]{1,16}"); }

    static void cleanupPending(File library) {
        File[] folders = library.listFiles();
        if (folders == null) return;
        for (File folder : folders) {
            if (!folder.isDirectory() || !folder.getName().matches("\\.pending-[a-fA-F0-9-]{36}")) continue;
            new File(folder, "map.zip").delete();
            new File(folder, "map.json").delete();
            folder.delete();
        }
    }

    static void validateZip(File file) throws IOException {
        boolean info = false;
        int entries = 0;
        long expanded = 0;
        try (ZipInputStream zip = new ZipInputStream(new FileInputStream(file))) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                if (++entries > 5000) throw new IOException("Too many ZIP entries");
                String name = entry.getName().replace('\\', '/');
                if (name.startsWith("/") || name.contains(":") || name.matches("(^|.*[/])\\.\\.([/].*|$)"))
                    throw new IOException("Unsafe ZIP path");
                boolean isInfo = !entry.isDirectory() && name.toLowerCase(Locale.ROOT).matches("(^|.*/)info\\.dat");
                if (isInfo && info) throw new IOException("Ambiguous map: multiple Info.dat files");
                long maximum = Math.min(isInfo ? 2L * 1024 * 1024 : 512L * 1024 * 1024, 512L * 1024 * 1024 - expanded);
                long size = copy(zip, new OutputStream() { public void write(int b) {} public void write(byte[] b, int o, int n) {} }, maximum);
                expanded += size;
                if (isInfo) { if (size == 0) throw new IOException("Empty Info.dat"); info = true; }
                zip.closeEntry(); // ZipInputStream verifies each file's CRC while reading.
            }
        }
        if (!info) throw new IOException("Not a Beat Saber map ZIP: Info.dat missing");
    }

    static String privateAddress(String value) throws IOException {
        String[] parts = value.trim().split("\\.", -1);
        if (parts.length != 4) throw new IOException("Enter the console's local IPv4 address");
        int[] octets = new int[4];
        for (int i = 0; i < 4; i++) {
            if (!parts[i].matches("[0-9]{1,3}")) throw new IOException("Invalid IPv4 address");
            octets[i] = Integer.parseInt(parts[i]);
            if (octets[i] > 255) throw new IOException("Invalid IPv4 address");
        }
        if (!(octets[0] == 10 || (octets[0] == 172 && octets[1] >= 16 && octets[1] <= 31) ||
              (octets[0] == 192 && octets[1] == 168))) throw new IOException("Use a private local-network address, not an Internet FTP server");
        return octets[0] + "." + octets[1] + "." + octets[2] + "." + octets[3];
    }

    static int port(String text) throws IOException {
        try { int p = Integer.parseInt(text.trim()); if (p > 0 && p <= 65535) return p; }
        catch (NumberFormatException ignored) {}
        throw new IOException("Port must be between 1 and 65535");
    }

    static void testConsole(String host, int port) throws IOException {
        host = privateAddress(host);
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(host, port), 5000);
            socket.setSoTimeout(5000);
            BufferedReader input = new BufferedReader(new InputStreamReader(socket.getInputStream(), "US-ASCII"));
            BufferedWriter output = new BufferedWriter(new OutputStreamWriter(socket.getOutputStream(), "US-ASCII"));
            if (reply(input) != 220) throw new IOException("Server is not ready for FTP login");
            output.write("USER anonymous\r\n"); output.flush();
            int code = reply(input);
            if (code == 331) { output.write("PASS orbeats-android@\r\n"); output.flush(); code = reply(input); }
            if (code != 230) throw new IOException("Anonymous FTP login was refused");
            output.write("QUIT\r\n"); output.flush();
        }
    }

    static int reply(BufferedReader input) throws IOException {
        long deadline = System.nanoTime() + 15_000_000_000L;
        String first = line(input, deadline);
        if (!first.matches("[0-9]{3}[ -].*")) throw new IOException("Invalid FTP response");
        int code = Integer.parseInt(first.substring(0, 3));
        if (first.charAt(3) == '-') {
            for (int i = 0; i < 64; i++) if (line(input, deadline).startsWith(first.substring(0, 3) + " ")) return code;
            throw new IOException("FTP response has too many lines");
        }
        return code;
    }

    private static String line(BufferedReader input, long deadline) throws IOException {
        StringBuilder text = new StringBuilder();
        for (int i = 0; i < 1024; i++) {
            if (System.nanoTime() > deadline) throw new SocketTimeoutException("FTP response timed out");
            int c = input.read();
            if (c == -1) throw new EOFException("FTP connection closed");
            if (c == '\n') return text.toString().replace("\r", "");
            text.append((char)c);
        }
        throw new IOException("FTP response line too long");
    }
}
