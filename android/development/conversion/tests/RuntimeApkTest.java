package dev.orbeats.android;

import android.app.Application;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.res.AssetManager;
import com.chaquo.python.Python;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.lang.reflect.Proxy;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.HashMap;
import java.util.Map;

/** Developer Android-framework harness, NOT an installed-Activity test. */
public final class RuntimeApkTest {
    public static final class ProbeApplication extends Application {
        private final AssetManager assets;
        private final File base, nativeDir;
        private final Map<String,String> values=new HashMap<>();
        private final SharedPreferences preferences;

        public ProbeApplication(String apk,String workspace,String nativePath) throws Exception {
            base=new File(workspace);nativeDir=new File(nativePath);
            assets=AssetManager.class.getDeclaredConstructor().newInstance();
            int cookie=(Integer)AssetManager.class.getMethod("addAssetPath",String.class).invoke(assets,apk);
            if(cookie==0)throw new AssertionError("AssetManager rejected APK");
            SharedPreferences.Editor editor=(SharedPreferences.Editor)Proxy.newProxyInstance(
                getClass().getClassLoader(),new Class<?>[]{SharedPreferences.Editor.class},(p,m,a)->{
                    switch(m.getName()){
                    case "putString":values.put((String)a[0],(String)a[1]);return p;
                    case "remove":values.remove((String)a[0]);return p;
                    case "apply":return null;
                    case "commit":return true;
                    default:throw new AssertionError("Unexpected Editor call: "+m.getName());
                    }
                });
            preferences=(SharedPreferences)Proxy.newProxyInstance(getClass().getClassLoader(),
                new Class<?>[]{SharedPreferences.class},(p,m,a)->{
                    switch(m.getName()){
                    case "getString":return values.containsKey(a[0])?values.get(a[0]):a[1];
                    case "edit":return editor;
                    default:throw new AssertionError("Unexpected preferences call: "+m.getName());
                    }
                });
        }
        @Override public Context getApplicationContext(){return this;}
        @Override public AssetManager getAssets(){return assets;}
        @Override public android.content.res.Resources getResources(){return android.content.res.Resources.getSystem();}
        @Override public android.content.res.Resources.Theme getTheme(){return getResources().newTheme();}
        @Override public boolean isUiContext(){return false;}
        @Override public Object getSystemService(String name){return null;}
        @Override public android.os.Looper getMainLooper(){return android.os.Looper.getMainLooper();}
        @Override public String getOpPackageName(){return getPackageName();}
        @Override public int checkCallingOrSelfPermission(String permission){return android.content.pm.PackageManager.PERMISSION_DENIED;}
        public int getUserId(){return android.os.Process.myUid()/100000;}
        @Override public ClassLoader getClassLoader(){return getClass().getClassLoader();}
        @Override public File getFilesDir(){File d=new File(base,"files");d.mkdirs();return d;}
        @Override public File getCacheDir(){File d=new File(base,"cache");d.mkdirs();return d;}
        @Override public String getPackageName(){return "dev.orbeats.android";}
        @Override public ApplicationInfo getApplicationInfo(){ApplicationInfo i=new ApplicationInfo();i.nativeLibraryDir=nativeDir.getAbsolutePath();return i;}
        @Override public SharedPreferences getSharedPreferences(String name,int mode){return preferences;}
    }
    public static void main(String[] args) {
        try{run(args);}catch(Throwable error){error.printStackTrace(System.err);System.exit(1);}
    }
    private static void checkVisibility(Context app){
        if(android.os.Looper.myLooper()==null)android.os.Looper.prepareMainLooper();
        Context context=new android.view.ContextThemeWrapper(app,android.R.style.Theme_Material);
        android.widget.FrameLayout viewport=new android.widget.FrameLayout(context);
        android.view.View song=new android.view.View(context);song.setTag("song:a");viewport.addView(song);
        viewport.layout(0,0,100,100);song.layout(0,80,100,140);
        if(!MainActivity.visibleSong(viewport,"a")||MainActivity.visibleSong(viewport,"b"))throw new AssertionError("Partial/wrong song visibility");
        viewport.scrollTo(0,140);
        if(MainActivity.visibleSong(viewport,"a"))throw new AssertionError("Fully scrolled-out song still visible");
        viewport.scrollTo(0,139);
        if(!MainActivity.visibleSong(viewport,"a"))throw new AssertionError("Last visible pixel stopped song");
        song.setVisibility(android.view.View.GONE);
        if(MainActivity.visibleSong(viewport,"a"))throw new AssertionError("Hidden song still visible");
        song.setVisibility(android.view.View.VISIBLE);viewport.removeView(song);
        if(MainActivity.visibleSong(viewport,"a"))throw new AssertionError("Removed row still visible");
        android.widget.FrameLayout carousel=new android.widget.FrameLayout(context);viewport.addView(carousel);carousel.addView(song);
        viewport.scrollTo(0,0);carousel.layout(0,0,100,100);song.layout(100,0,200,100);
        if(MainActivity.visibleSong(viewport,"a"))throw new AssertionError("Offscreen carousel song visible");
        carousel.scrollTo(99,0);
        if(!MainActivity.visibleSong(viewport,"a"))throw new AssertionError("Partial carousel song hidden");
        carousel.setVisibility(android.view.View.GONE);
        if(MainActivity.visibleSong(viewport,"a"))throw new AssertionError("Hidden ancestor ignored");
        android.view.View duplicate=new android.view.View(context);duplicate.setTag("song:a");viewport.addView(duplicate);duplicate.layout(0,0,100,40);
        if(!MainActivity.visibleSong(viewport,"a"))throw new AssertionError("Visible duplicate must keep preview");
        System.out.println("PASS: production song visibility; vertical/horizontal clipping, partial pixel, hidden/removed/wrong rows (framework geometry, not installed scrolling)");
    }
    private static void checkCompatibility() throws Exception {
        JSONObject diff=new JSONObject();JSONObject map=new JSONObject().put("versions",new JSONArray().put(new JSONObject().put("state","Published").put("diffs",new JSONArray().put(diff))));
        if(!MainActivity.metadataIncompatibility(map).isEmpty())throw new AssertionError("Unflagged map misclassified");
        diff.put("ne",true);if(!MainActivity.metadataIncompatibility(map).contains("Noodle"))throw new AssertionError("Noodle warning missing");
        diff.put("ne",false).put("me",true);if(!MainActivity.metadataIncompatibility(map).contains("Mapping"))throw new AssertionError("Mapping warning missing");
        if(!MainActivity.unsupportedMapError("ValueError: unsupported V3 features: arcs")||!MainActivity.unsupportedMapError("unsupported requirements/custom metadata")||MainActivity.unsupportedMapError("FTP timeout")||MainActivity.unsupportedMapError("Unsupported OrBeats library capability")||MainActivity.unsupportedMapError("song file escapes input directory or is missing"))throw new AssertionError("Compatibility error classification");
        if(System.getenv("ORBEATS_MAP_ID_PROBE")!=null){
            JSONArray maps=MainActivity.searchMaps("25975",0,"Relevance",true);
            if(maps.length()!=1||!maps.getJSONObject(0).getString("id").equals("25975")||!MainActivity.metadataIncompatibility(maps.getJSONObject(0)).contains("Noodle"))throw new AssertionError("Live ID lookup failed");
            System.out.println("PASS: actual APK direct BeatSaver ID 25975 lookup and Noodle metadata warning; not installed UI");
        }
        if(!MainActivity.mapSize(8256660).contains("8.26 MB")||!MainActivity.mapSize(-1).contains("unavailable"))throw new AssertionError("Download size formatting");
        if(System.getenv("ORBEATS_MAP_ID_PROBE")!=null){try{long size=Core.downloadSize("https://r2cdn.beatsaver.com/81640134dc065ba081740189c2ebb785849bea61.zip");if(size>0&&size!=8256660)throw new AssertionError("BeatSaver HEAD size mismatch");}catch(java.io.IOException unavailable){System.out.println("UNAVAILABLE: live BeatSaver size header: "+unavailable);}}
        System.out.println("PASS: production known-incompatibility metadata and download size formatting/optional trusted HEAD; unknown stays unclassified");
    }
    private static void checkCatalog(Context app) throws Exception {
        JSONArray songs=new JSONArray();for(int i=0;i<39;i++)songs.put(new JSONObject().put("id",String.format(java.util.Locale.ROOT,"bsd_additive_%024x",i)).put("title","Console song "+i).put("author","Artist "+i));
        JSONObject catalog=new JSONObject().put("host","192.168.1.2").put("port","2121").put("read_at",1234).put("snapshot",new JSONObject().put("songs",songs));
        SharedPreferences prefs=app.getSharedPreferences("catalog-test",0);prefs.edit().putString("consoleCatalog",catalog.toString()).apply();
        JSONObject restored=new JSONObject(prefs.getString("consoleCatalog","{}"));
        JSONArray displayed=MainActivity.catalogSongs(restored,"192.168.1.2","2121");
        if(displayed==null||displayed.length()!=39||!displayed.getJSONObject(38).getString("title").equals("Console song 38"))throw new AssertionError("Console songs not retained for Library");
        if(MainActivity.catalogSongs(restored," 192.168.001.2 ","02121")==null)throw new AssertionError("Equivalent saved endpoint rejected");
        if(MainActivity.catalogSongs(restored,"192.168.1.3","2121")!=null||MainActivity.catalogSongs(restored,"192.168.1.2","2122")!=null)throw new AssertionError("Wrong console catalog shown");
        if(MainActivity.catalogSongs(restored,"","2121")!=null||MainActivity.catalogSongs(restored,"192.168.1.2","bad")!=null||MainActivity.catalogSongs(new JSONObject(),"192.168.1.2","2121")!=null)throw new AssertionError("Missing/invalid endpoint catalog shown");
        restored.put("snapshot",new JSONObject());if(MainActivity.catalogSongs(restored,"192.168.1.2","2121")!=null)throw new AssertionError("Missing songs array accepted");
        restored.put("snapshot",new JSONObject().put("songs",new JSONArray()));if(MainActivity.catalogSongs(restored,"192.168.1.2","2121").length()!=0)throw new AssertionError("Empty PS4 library lost");
        System.out.println("PASS: production Library catalog selection, 39-song preferences round-trip, endpoint isolation, missing/invalid/empty snapshot; NOT installed card rendering");
    }
    private static void run(String[] args) throws Exception {
        ProbeApplication app=new ProbeApplication(args[0],args[1],args[2]);
        checkVisibility(app);checkCatalog(app);checkCompatibility();
        String first=ConversionRuntime.check(app);
        String again=ConversionRuntime.check(app);
        if(!first.equals(again) || !first.contains("Conversion runtime check passed"))throw new AssertionError("Repeated JNI check mismatch");
        File[] leftovers=app.getCacheDir().listFiles((d,n)->n.startsWith("orbeats-engine-"));
        if(leftovers==null || leftovers.length!=0)throw new AssertionError("Self-check temporary files not cleaned");
        if(args.length>3){
            ConversionRuntime.validateTemplate(app,new File(System.getenv("ORBEATS_SONG_PROBE_TEMPLATE")));
            File badTemplate=new File(app.getCacheDir(),"invalid-template");Files.write(badTemplate.toPath(),new byte[]{'x',0});
            try{ConversionRuntime.validateTemplate(app,badTemplate);throw new AssertionError("Bad template accepted");}
            catch(com.chaquo.python.PyException expected){if(!expected.toString().contains("UnityFS"))throw expected;}
            finally{badTemplate.delete();}
            System.out.println("PASS: production Java template validation and invalid-source refusal");
            Python.getInstance().getModule("runpy").callAttr("run_path",args[3]);
            JSONArray cases=new JSONArray(new String(Files.readAllBytes(new File(System.getenv("ORBEATS_SONG_PROBE_ROOT"),"results.json").toPath()),StandardCharsets.UTF_8));
            for(int i=0;i<cases.length();i++){
                JSONObject entry=cases.getJSONObject(i);
                JSONObject prepared=ConversionRuntime.prepare(app,new File(entry.getString("zip")),entry.getString("hash"),new File(entry.getBoolean("template")?System.getenv("ORBEATS_SONG_PROBE_TEMPLATE"):"/nonexistent"));
                if(prepared.getBoolean("bundle_created")!=entry.getBoolean("template")||prepared.getJSONObject("note_counts").getInt("ExpertPlus")!=entry.getJSONObject("report").getJSONObject("note_counts").getInt("ExpertPlus"))throw new AssertionError("Java preparation report mismatch");
            }
            JSONObject qualityCase=cases.getJSONObject(0);
            JSONObject selected=ConversionRuntime.prepare(app,new File(qualityCase.getString("zip")),qualityCase.getString("hash"),new File(System.getenv("ORBEATS_SONG_PROBE_TEMPLATE")),"balanced");
            if(!selected.getString("audio_quality").equals("balanced")||!selected.getString("audio_codec").equals("vorbis"))throw new AssertionError("Java selected quality lost");
            System.out.println("PASS: production Java preparation bridge, six V2/V3/V4 preparations and explicit balanced-quality keyword");
            if(args.length>4){
                com.chaquo.python.PyObject probe=Python.getInstance().getModule("runpy").callAttr("run_path",args[4]);
                try{
                    JSONObject snapshot=ConversionRuntime.consoleStatus(app,"192.168.1.2",2121);
                    byte[] cover=ConversionRuntime.consoleCover(app,"192.168.1.2",2121,snapshot.getJSONArray("songs").getJSONObject(0));
                    if(cover.length!=snapshot.getJSONArray("songs").getJSONObject(0).getInt("cover_bytes"))throw new AssertionError("Java cover bytes mismatch");
                    if(snapshot.getJSONArray("songs").length()!=1||!snapshot.getBoolean("read_only"))throw new AssertionError("Java status mismatch");
                    JSONObject entry=new JSONObject(new String(Files.readAllBytes(new File(System.getenv("ORBEATS_SONG_PROBE_ROOT"),"console-bridge.json").toPath()),StandardCharsets.UTF_8));
                    JSONObject result=ConversionRuntime.install(app,"192.168.1.2",2121,new File(entry.getString("zip")),entry.getString("hash"),new File("/nonexistent"),snapshot,"small");
                    if(!result.getBoolean("ok")||result.getInt("count")!=2||!result.getString("audio_quality").equals("small")||!result.getString("audio_codec").equals("vorbis"))throw new AssertionError("Java quality install mismatch");
                    if(ConversionRuntime.consoleStatus(app,"192.168.1.2",2121).getJSONArray("songs").length()!=2)throw new AssertionError("Java catalog after install mismatch");
                    if(!new File(app.getFilesDir(),"console-recovery/transactions").isDirectory())throw new AssertionError("Recovery not in persistent files storage");
                    JSONObject after=ConversionRuntime.consoleStatus(app,"192.168.1.2",2121);
                    ConversionRuntime.remove(app,"192.168.1.2",2121,snapshot.getJSONArray("songs").getJSONObject(0).getString("id"),after);
                    if(ConversionRuntime.consoleStatus(app,"192.168.1.2",2121).getJSONArray("songs").length()!=1)throw new AssertionError("Java removal bridge mismatch");
                    System.out.println("PASS: production Java status/confirmed-install/removal bridges; simulated FTP only, durable files-directory recovery");
                }finally{probe.callAttr("get","restore_console_probe").call();}
            }
        }
        Thread.currentThread().interrupt();
        try{ConversionRuntime.check(app);throw new AssertionError("Interrupted check accepted");}
        catch(java.io.InterruptedIOException expected){}finally{Thread.interrupted();}
        Files.write(new File(args[1],"RESULT.txt").toPath(),("PASS: APK AssetManager + official AndroidPlatform/JNI + in-app generated writer check twice; temporary cleanup and interruption gate.\nDeveloper simulated Application context, NOT installed APK/Activity/lifecycle evidence.\n\n"+first+"\n").getBytes(StandardCharsets.UTF_8));
        System.out.println("PASS: APK AssetManager/AndroidPlatform/JNI self-check (developer context, not installed Activity)");
    }
}
