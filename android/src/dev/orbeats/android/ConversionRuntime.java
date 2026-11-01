package dev.orbeats.android;

import android.content.Context;
import com.chaquo.python.Python;
import com.chaquo.python.Kwarg;
import com.chaquo.python.android.AndroidPlatform;
import java.io.File;
import java.io.InterruptedIOException;
import org.json.JSONObject;

/** Lazy, serialized in-process conversion and explicitly requested console operations. */
final class ConversionRuntime {
    private ConversionRuntime() {}

    private static Python start(Context context) throws InterruptedIOException {
        if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Cancelled");
        if (!Python.isStarted()) Python.start(new AndroidPlatform(context.getApplicationContext()));
        return Python.getInstance();
    }

    static synchronized JSONObject prepare(Context context, File archive, String hash, File template) throws Exception {
        return prepare(context,archive,hash,template,"original");
    }

    static synchronized JSONObject prepare(Context context, File archive, String hash, File template, String quality) throws Exception {
        String raw=start(context).getModule("song_loader").callAttr("prepare",archive.getAbsolutePath(),hash,
            new File(context.getCacheDir(),"prepared-songs").getAbsolutePath(),template.isFile()?template.getAbsolutePath():"",new Kwarg("quality",quality)).toString();
        if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Cancelled");
        return new JSONObject(raw);
    }

    static synchronized JSONObject consoleStatus(Context context, String host, int port) throws Exception {
        String raw=start(context).getModule("console_library").callAttr("status",host,port).toString();
        return new JSONObject(raw);
    }

    static synchronized byte[] consoleCover(Context context,String host,int port,JSONObject song) throws Exception {
        return start(context).getModule("console_library").callAttr("cover",host,port,song.getString("id"),song.getInt("cover_bytes"),song.getString("cover_fnv")).toJava(byte[].class);
    }

    static synchronized JSONObject install(Context context, String host, int port, File archive, String hash, File template, JSONObject confirmed) throws Exception {
        return install(context,host,port,archive,hash,template,confirmed,"original");
    }

    static synchronized JSONObject install(Context context, String host, int port, File archive, String hash, File template, JSONObject confirmed, String quality) throws Exception {
        String raw=start(context).getModule("console_library").callAttr("install",host,port,archive.getAbsolutePath(),hash,
            new File(context.getFilesDir(),"console-recovery").getAbsolutePath(),new File(context.getCacheDir(),"console-work").getAbsolutePath(),
            template.isFile()?template.getAbsolutePath():"",confirmed.getString("library_sha256"),confirmed.getString("plugin_sha256"),quality).toString();
        // Do not turn a completed remote commit into an interruption error.
        return new JSONObject(raw);
    }

    static synchronized JSONObject remove(Context context, String host, int port, String id, JSONObject confirmed) throws Exception {
        return new JSONObject(start(context).getModule("console_library").callAttr("remove",host,port,id,
            new File(context.getFilesDir(),"console-recovery").getAbsolutePath(),confirmed.getString("library_sha256"),confirmed.getString("plugin_sha256")).toString());
    }

    static synchronized JSONObject installPlugin(Context context, String host, int port, String kind) throws Exception {
        return new JSONObject(start(context).getModule("console_library").callAttr("install_plugin",host,port,kind,
            new File(context.getFilesDir(),"console-recovery").getAbsolutePath()).toString());
    }

    static synchronized void validateTemplate(Context context, File template) throws Exception {
        start(context).getModule("song_loader").callAttr("validate_template",template.getAbsolutePath());
        if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Cancelled");
    }

    static synchronized String check(Context context) throws Exception {
        start(context);
        String raw=Python.getInstance().getModule("conversion_runtime")
            .callAttr("check",context.getCacheDir().getAbsolutePath()).toString();
        JSONObject report=new JSONObject(raw);
        if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Cancelled");
        return "Conversion runtime check passed\n\nPython "+report.getString("python").split("\\n",2)[0]
            +"\nUnityPy "+report.getString("unitypy")
            +"\n\nGenerated type-tree read/write and truncated-input refusal"
            +"\nUnityFS edit/reopen: none, LZ4, LZMA, original"
            +"\nNative LZ4/Brotli and 512px PNG round-trips"
            +"\n\nGenerated test data only. This does not convert a downloaded song or prove a real PS4 template works. No console connection or writes.";
    }
}
