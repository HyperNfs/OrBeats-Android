package dev.orbeats.android;

import android.app.*;
import android.content.*;
import android.content.res.ColorStateList;
import android.animation.*;
import android.graphics.*;
import android.graphics.drawable.*;
import android.media.MediaPlayer;
import android.os.*;
import android.view.*;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.view.animation.OvershootInterpolator;
import android.text.TextUtils;
import android.widget.*;
import android.util.LruCache;
import org.json.*;
import java.io.*;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/** Native phone companion. No WebView, localhost server or Termux runtime. */
public final class MainActivity extends Activity {
    private int BG, BAR, CARD, TONAL, GREEN, WHITE, MUTED;
    private boolean lightMode;
    private ListView list;
    private final ExecutorService work=Executors.newFixedThreadPool(2);
    // Keep cover requests bounded during fast scrolling.
    private final ExecutorService images=new ThreadPoolExecutor(2,2,0L,TimeUnit.MILLISECONDS,new ArrayBlockingQueue<Runnable>(32),new ThreadPoolExecutor.DiscardOldestPolicy());
    private final LruCache<String,Bitmap> covers=new LruCache<>(32);
    private final ArrayList<JSONObject> maps=new ArrayList<>();
    private final Set<String> downloading=Collections.synchronizedSet(new HashSet<>());
    private LinearLayout root, body, bottom, footer;
    private final ArrayList<JSONObject> displayed=new ArrayList<>();
    private BaseAdapter adapter;
    private TextView status;
    private EditText search;
    private Button searchMode;
    private boolean searchById;
    private int tab, page, generation, renderedTab=-1;
    private boolean loading, ended, preparingSong, showPs4Library=true;
    private JSONObject consoleCatalog=new JSONObject();
    private AlertDialog installProgress;
    private File exportSource;
    private String query="", order="Curated";
    private File library, previewFile;
    private MediaPlayer player;
    private final PreviewState playback=new PreviewState();
    private android.content.SharedPreferences prefs;

    @Override public void onCreate(Bundle state) {
        prefs=getSharedPreferences("orbeats",MODE_PRIVATE);
        lightMode=prefs.getBoolean("lightMode",false);
        setTheme(lightMode?R.style.LightTheme:R.style.AppTheme);
        super.onCreate(state);
        library=new File(getFilesDir(),"songs");
        if (!library.isDirectory() && !library.mkdirs()) { dialog().setMessage("Cannot create the private song library").setPositiveButton("Close",(d,w)->finish()).show(); return; }
        Core.cleanupPending(library);
        if(state!=null && state.getString("exportSource")!=null)exportSource=new File(state.getString("exportSource"));
        query=prefs.getString("query","");
        searchById=prefs.getBoolean("searchById",false);
        try{consoleCatalog=new JSONObject(prefs.getString("consoleCatalog","{}"));}catch(JSONException ignored){}
        buildUi();load(true);
    }

    private void buildUi(){
        String draft=search==null?query:search.getText().toString();
        setTheme(lightMode?R.style.LightTheme:R.style.AppTheme);
        BG=lightMode?0xfff7faf2:0xff101710;BAR=lightMode?0xffeef3e9:0xff19241c;
        CARD=lightMode?0xffe4eddd:0xff223329;TONAL=lightMode?0xffdcebd3:0xff334c38;
        GREEN=lightMode?0xff386a20:0xffb4df9b;WHITE=lightMode?0xff172217:0xffecf2e8;MUTED=lightMode?0xff52624f:0xffb3c1af;
        getWindow().setBackgroundDrawable(new ColorDrawable(BG));
        getWindow().setStatusBarColor(BG); getWindow().setNavigationBarColor(BAR);
        if(Build.VERSION.SDK_INT>=28)getWindow().setNavigationBarDividerColor(BAR);
        if(Build.VERSION.SDK_INT>=29)getWindow().setNavigationBarContrastEnforced(false);
        View decor=getWindow().getDecorView();int flags=View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
        decor.setSystemUiVisibility((decor.getSystemUiVisibility()&~flags)|(lightMode?flags:0));
        root=column(); root.setBackgroundColor(BG);
        root.setOnApplyWindowInsetsListener((v,insets)->{ v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),0);if(bottom!=null)bottom.setPadding(0,0,0,insets.getSystemWindowInsetBottom());return insets; });
        setContentView(root);
        FrameLayout header=new FrameLayout(this);
        root.addView(header,new LinearLayout.LayoutParams(-1,dp(68)));
        LinearLayout wordmark=row();wordmark.setGravity(Gravity.CENTER);
        wordmark.addView(new Logo(),new LinearLayout.LayoutParams(dp(28),dp(28)));
        TextView brand=text("OrBeats",24,WHITE);brand.setTypeface(Typeface.create("sans-serif",Typeface.BOLD));
        brand.setPadding(dp(8),0,0,0);brand.setMaxLines(1);
        brand.setMaxWidth(Math.max(dp(70),getResources().getDisplayMetrics().widthPixels-dp(176)));
        brand.setAutoSizeTextTypeUniformWithConfiguration(18,24,1,android.util.TypedValue.COMPLEX_UNIT_SP);
        wordmark.addView(brand);header.addView(wordmark,new FrameLayout.LayoutParams(-2,-1,Gravity.CENTER));
        LinearLayout actions=row();
        actions.addView(icon(R.drawable.ic_help,"How to link your console",v->tutorial()));
        FrameLayout.LayoutParams actionParams=new FrameLayout.LayoutParams(-2,-1,Gravity.END|Gravity.CENTER_VERTICAL);actionParams.rightMargin=dp(8);header.addView(actions,actionParams);
        searchMode=button(searchById?"Search by ID ▾":"Search by name ▾",v->dialog().setTitle("Search by")
            .setSingleChoiceItems(new String[]{"Name / artist / mapper","BeatSaver ID"},searchById?1:0,(d,w)->{searchById=w==1;prefs.edit().putBoolean("searchById",searchById).apply();searchMode.setText(searchById?"Search by ID ▾":"Search by name ▾");search.setHint(searchById?"BeatSaver ID, e.g. 25975":"Songs, artists or mappers");d.dismiss();query=search.getText().toString().trim();load(true);}).setNegativeButton("Close",null).show());
        LinearLayout.LayoutParams modeParams=new LinearLayout.LayoutParams(-2,dp(48));modeParams.setMargins(dp(16),0,dp(16),dp(8));root.addView(searchMode,modeParams);
        search=new EditText(this);search.setSingleLine(true);search.setTextSize(15);search.setTextColor(WHITE);search.setHintTextColor(MUTED);
        search.setHint(searchById?"BeatSaver ID, e.g. 25975":"Songs, artists or mappers");search.setPadding(dp(18),0,dp(18),0);search.setBackground(shape(BAR,28));
        Drawable searchIcon=getDrawable(R.drawable.ic_search);searchIcon.setTint(MUTED);searchIcon.setBounds(0,0,dp(22),dp(22));
        search.setCompoundDrawables(searchIcon,null,null,null);search.setCompoundDrawablePadding(dp(12));
        search.setText(draft);search.setImeOptions(EditorInfo.IME_ACTION_SEARCH);
        LinearLayout.LayoutParams searchParams=new LinearLayout.LayoutParams(-1,dp(56));searchParams.setMargins(dp(16),0,dp(16),dp(8));root.addView(search,searchParams);
        search.setOnEditorActionListener((v,action,event)->{if(action==EditorInfo.IME_ACTION_SEARCH){query=search.getText().toString().trim();order="Relevance";((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(search.getWindowToken(),0);search.clearFocus();load(true);return true;}return false;});
        list=new ListView(this);list.setDivider(null);list.setCacheColorHint(Color.TRANSPARENT);
        body=column();body.setPadding(dp(16),dp(12),dp(16),dp(16));footer=column();footer.setPadding(dp(16),0,dp(16),dp(16));
        list.addHeaderView(body,null,false);list.addFooterView(footer,null,false);
        adapter=new BaseAdapter(){
            public int getCount(){return displayed.size();}
            public Object getItem(int position){return displayed.get(position);}
            public long getItemId(int position){return position;}
            // shortcut: rebuild simple rows; use view holders if device profiling shows scroll jank.
            public View getView(int position,View reusable,ViewGroup parent){return tab==1&&showPs4Library?consoleSongCard(displayed.get(position)):songCard(displayed.get(position),tab==1);}
        };
        list.setAdapter(adapter);root.addView(list,new LinearLayout.LayoutParams(-1,0,1));
        bottom=row();bottom.setBackgroundColor(BAR);root.addView(bottom);
        root.getViewTreeObserver().addOnPreDrawListener(()->{if(playback.phase!=PreviewState.Phase.STOPPED&&!visibleSong(list,playback.mapId))stopPreview();return true;});
        render();
    }

    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private LinearLayout column(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.VERTICAL);return v;}
    private LinearLayout row(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.HORIZONTAL);v.setGravity(Gravity.CENTER_VERTICAL);return v;}
    private TextView text(String s,int size,int color){TextView v=new TextView(this);v.setText(s);v.setTextSize(size);v.setTextColor(color);v.setTypeface(Typeface.create("sans-serif",Typeface.NORMAL));return v;}
    private GradientDrawable shape(int color,int radius){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;}
    private void gap(LinearLayout parent,int height){Space s=new Space(this);parent.addView(s,new LinearLayout.LayoutParams(1,dp(height)));}
    private Drawable ripple(int color,int radius){return new RippleDrawable(ColorStateList.valueOf(0x33000000|(GREEN&0x00ffffff)),shape(color,radius),shape(Color.WHITE,radius));}
    private AlertDialog.Builder dialog(){
        return new AlertDialog.Builder(this){
            @Override public AlertDialog create(){
                AlertDialog result=super.create();
                result.setOnShowListener(d->{for(int action:new int[]{AlertDialog.BUTTON_POSITIVE,AlertDialog.BUTTON_NEGATIVE,AlertDialog.BUTTON_NEUTRAL}){Button button=result.getButton(action);if(button!=null)pressMotion(button);}});
                return result;
            }
        };
    }
    private void pressMotion(View view){
        StateListAnimator state=new StateListAnimator();
        AnimatorSet down=new AnimatorSet();down.playTogether(ObjectAnimator.ofFloat(view,"scaleX",.94f),ObjectAnimator.ofFloat(view,"scaleY",.94f));down.setDuration(100);
        AnimatorSet up=new AnimatorSet();up.playTogether(ObjectAnimator.ofFloat(view,"scaleX",1f),ObjectAnimator.ofFloat(view,"scaleY",1f));up.setDuration(280);up.setInterpolator(new OvershootInterpolator(1.1f));
        state.addState(new int[]{android.R.attr.state_pressed,android.R.attr.state_enabled},down);state.addState(new int[]{},up);view.setStateListAnimator(state);
    }
    private ImageButton icon(int resource,String description,View.OnClickListener listener){ImageButton b=new ImageButton(this);b.setImageResource(resource);b.setColorFilter(MUTED);b.setBackground(ripple(Color.TRANSPARENT,24));b.setPadding(dp(12),dp(12),dp(12),dp(12));b.setContentDescription(description);b.setOnClickListener(listener);b.setLayoutParams(new LinearLayout.LayoutParams(dp(48),dp(48)));pressMotion(b);return b;}
    private Button button(String label,View.OnClickListener click){Button b=new Button(this);b.setText(label);b.setTextSize(14);b.setTextColor(GREEN);b.setAllCaps(false);b.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));b.setMinHeight(dp(48));b.setMinimumWidth(0);b.setPadding(dp(18),0,dp(18),0);b.setBackgroundTintList(null);b.setBackground(ripple(TONAL,24));b.setOnClickListener(click);pressMotion(b);return b;}
    private ImageView artwork(JSONObject map,int radius){ImageView art=new ImageView(this);art.setImageResource(R.drawable.icon);art.setBackground(shape(BAR,radius));art.setClipToOutline(true);art.setScaleType(ImageView.ScaleType.CENTER_CROP);art.setContentDescription("Cover for "+title(map));cover(art,version(map).optString("coverURL"));return art;}
    private void message(String text){if(!ended)Toast.makeText(this,text,Toast.LENGTH_LONG).show();}
    private void ui(Runnable action){runOnUiThread(()->{if(!ended && !isFinishing())action.run();});}
    private String str(JSONObject o,String name,String fallback){String s=o.optString(name,"");return s.isEmpty()?fallback:s;}
    private JSONObject metadata(JSONObject map){JSONObject m=map.optJSONObject("metadata");return m==null?new JSONObject():m;}
    private static JSONObject version(JSONObject map){JSONArray list=map.optJSONArray("versions");if(list!=null)for(int i=0;i<list.length();i++){JSONObject v=list.optJSONObject(i);if(v!=null && "Published".equals(v.optString("state")))return v;}return new JSONObject();}
    static String metadataIncompatibility(JSONObject map){
        JSONArray diffs=version(map).optJSONArray("diffs");
        if(diffs!=null)for(int i=0;i<diffs.length();i++){
            JSONObject diff=diffs.optJSONObject(i);if(diff==null)continue;
            if(diff.optBoolean("ne"))return "Not supported: Noodle Extensions (BeatSaver metadata)";
            if(diff.optBoolean("me"))return "Not supported: Mapping Extensions (BeatSaver metadata)";
        }
        return "";
    }
    private String incompatibility(JSONObject map){return prefs.getString("unsupported:"+version(map).optString("hash"),metadataIncompatibility(map));}
    private int warningColor(){return prefs.getBoolean("lightMode",false)?0xffb3261e:0xffffb4ab;}
    private void rememberIncompatibility(JSONObject map,Throwable error){
        String reason=error.toString();
        if(unsupportedMapError(reason)){
            String hash=version(map).optString("hash");if(!hash.isEmpty())prefs.edit().putString("unsupported:"+hash,reason).apply();
        }
    }
    static boolean unsupportedMapError(String reason){
        return reason.matches("(?s).*(unsupported V[234] |unsupported requirements/custom metadata|mod requirements unsupported|mod/environment requirements unsupported|unsupported legacy custom data|unsupported FX events|unsupported light keywords|unsupported editor bookmark fields).*?");
    }
    private String title(JSONObject map){return str(metadata(map),"songName",str(map,"name","Untitled"));}
    private String artist(JSONObject map){return str(metadata(map),"songAuthorName","Unknown artist");}
    private File songDir(JSONObject map){String id=map.optString("id");return Core.validId(id)?new File(library,id.toLowerCase(Locale.ROOT)):null;}
    private boolean installed(JSONObject map){File f=songDir(map);return f!=null && new File(f,"map.zip").isFile() && new File(f,"map.json").isFile();}
    private String rating(JSONObject map){JSONObject stats=map.optJSONObject("stats");int percent=Core.scorePercent(stats==null?Double.NaN:stats.optDouble("score",Double.NaN));return percent<0?"No rating yet":"\u2661 "+percent+"%";}

    private void render(){
        if(body==null)return;
        if(renderedTab>=0&&renderedTab!=tab)stopPreview();
        body.removeAllViews();bottom.removeAllViews();footer.removeAllViews();displayed.clear();
        search.setVisibility(tab==0?View.VISIBLE:View.GONE);searchMode.setVisibility(tab==0?View.VISIBLE:View.GONE);
        String[] names={"Discover","Library","Settings"};
        int[] symbols={R.drawable.ic_explore,R.drawable.ic_library,R.drawable.ic_settings};
        boolean animate=renderedTab>=0&&renderedTab!=tab;renderedTab=tab;
        for(int i=0;i<3;i++){
            final int target=i;boolean selected=i==tab;
            LinearLayout nav=column();nav.setGravity(Gravity.CENTER);nav.setBackground(ripple(Color.TRANSPARENT,24));
            nav.setSelected(selected);nav.setFocusable(true);nav.setContentDescription(names[i]);
            FrameLayout indicator=new FrameLayout(this);if(selected)indicator.setBackground(shape(TONAL,18));
            ImageView symbol=new ImageView(this);symbol.setImageResource(symbols[i]);symbol.setColorFilter(selected?GREEN:MUTED);
            indicator.addView(symbol,new FrameLayout.LayoutParams(dp(24),dp(24),Gravity.CENTER));
            nav.addView(indicator,new LinearLayout.LayoutParams(dp(64),dp(32)));gap(nav,4);
            TextView label=text(names[i],12,selected?GREEN:MUTED);label.setGravity(Gravity.CENTER);
            label.setTypeface(Typeface.create(selected?"sans-serif-medium":"sans-serif",Typeface.NORMAL));nav.addView(label);
            symbol.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);label.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
            nav.setOnClickListener(v->{if(tab!=target){tab=target;render();if(tab==1&&showPs4Library&&catalogSongs(consoleCatalog,prefs.getString("host",""),prefs.getString("port","2121"))==null&&!prefs.getString("host","").isEmpty()&&!preparingSong)consoleCheck(null);}});pressMotion(nav);
            bottom.addView(nav,new LinearLayout.LayoutParams(0,dp(80),1));
            if(selected&&animate){indicator.setScaleX(.75f);indicator.setScaleY(.8f);indicator.animate().scaleX(1).scaleY(1).setDuration(280).setInterpolator(new OvershootInterpolator(.6f)).start();}
        }
        if(tab==2){settings();adapter.notifyDataSetChanged();return;}
        if(tab==1){renderLibrary();adapter.notifyDataSetChanged();return;}
        if(!maps.isEmpty())featured();
        LinearLayout filter=row();TextView heading=text(query.isEmpty()?"Find your next beat":"Search results",22,WHITE);
        heading.setTypeface(Typeface.create("sans-serif",Typeface.BOLD));heading.setMinHeight(dp(64));heading.setGravity(Gravity.CENTER_VERTICAL);filter.addView(heading,new LinearLayout.LayoutParams(0,-2,1));
        Button filterButton=button("Filter",v->filters());Drawable tune=getDrawable(R.drawable.ic_tune);tune.setTint(GREEN);tune.setBounds(0,0,dp(18),dp(18));filterButton.setCompoundDrawables(tune,null,null,null);filterButton.setCompoundDrawablePadding(dp(8));filter.addView(filterButton);body.addView(filter);
        status=text(loading?"Finding your flow\u2026":maps.isEmpty()?"No maps found. Try a different search.":order+" \u00b7 Live from BeatSaver",12,MUTED);body.addView(status);gap(body,16);
        displayed.addAll(maps);
        if(!maps.isEmpty()&&!searchById){Button more=button(loading?"Loading\u2026":"More beats",v->load(false));more.setEnabled(!loading);footer.addView(more);gap(footer,8);}
        footer.addView(button("Refresh maps",v->load(true)));adapter.notifyDataSetChanged();
    }

    private void featured(){
        HorizontalScrollView carousel=new HorizontalScrollView(this);carousel.setHorizontalScrollBarEnabled(false);
        LinearLayout items=row();carousel.addView(items);
        int width=Math.max(dp(240),getResources().getDisplayMetrics().widthPixels-dp(52));
        int count=Math.min(3,maps.size());
        for(int i=0;i<count;i++){
            JSONObject map=maps.get(i);LinearLayout card=column();card.setTag("song:"+map.optString("id"));card.setBackground(ripple(CARD,32));card.setPadding(dp(20),dp(20),dp(20),dp(16));
            int height=224+Math.round(Math.max(0f,getResources().getConfiguration().fontScale-1f)*120);
            LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(width,dp(height));params.setMargins(0,0,dp(12),0);items.addView(card,params);
            LinearLayout top=row(),copy=column();copy.setPadding(0,0,dp(14),0);
            TextView caption=text(order.equals("Curated")?"CURATED PICKS":"ON YOUR RADAR",11,GREEN);caption.setLetterSpacing(.1f);copy.addView(caption);gap(copy,12);
            TextView name=text(title(map),25,incompatibility(map).isEmpty()?WHITE:warningColor());name.setTypeface(Typeface.create("sans-serif",Typeface.BOLD));name.setMaxLines(2);name.setEllipsize(TextUtils.TruncateAt.END);copy.addView(name);
            top.addView(copy,new LinearLayout.LayoutParams(0,-2,1));int coverSize=width<dp(300)?88:104;
            top.addView(artwork(map,24),new LinearLayout.LayoutParams(dp(coverSize),dp(coverSize)));card.addView(top,new LinearLayout.LayoutParams(-1,0,1));
            LinearLayout meta=row();LinearLayout description=column();TextView author=text(artist(map),14,WHITE);author.setSingleLine(true);author.setEllipsize(TextUtils.TruncateAt.END);description.addView(author);gap(description,4);description.addView(text(rating(map),12,MUTED));meta.addView(description,new LinearLayout.LayoutParams(0,-2,1));meta.addView(previewButton(map));card.addView(meta);
            card.setOnClickListener(v->details(map));
        }
        body.addView(carousel);
        LinearLayout dots=row();dots.setGravity(Gravity.CENTER);dots.setPadding(0,dp(12),0,dp(4));
        for(int i=0;i<count;i++){View dot=new View(this);dot.setBackground(shape(i==0?GREEN:TONAL,3));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(dp(i==0?18:6),dp(6));p.setMargins(dp(3),0,dp(3),0);dots.addView(dot,p);}
        ArgbEvaluator colors=new ArgbEvaluator();
        carousel.setOnScrollChangeListener((v,x,y,oldX,oldY)->{
            float position=Math.min(count-1,Math.max(0,(count-1)*x/(float)Math.max(1,items.getWidth()-carousel.getWidth())));
            for(int i=0;i<count;i++){
                float weight=Math.max(0,1-Math.abs(position-i));View dot=dots.getChildAt(i);
                ((GradientDrawable)dot.getBackground()).setColor((Integer)colors.evaluate(weight,TONAL,GREEN));
                LinearLayout.LayoutParams p=(LinearLayout.LayoutParams)dot.getLayoutParams();p.width=dp(6)+Math.round(dp(12)*weight);dot.setLayoutParams(p);
            }
        });
        dots.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);body.addView(dots);
    }

    private LinearLayout songCard(JSONObject map,boolean local){
        LinearLayout wrapper=column();wrapper.setPadding(dp(16),0,dp(16),0);
        LinearLayout card=row();card.setTag("song:"+map.optString("id"));card.setPadding(dp(12),dp(14),dp(6),dp(14));card.setBackground(shape(BAR,26));wrapper.addView(card);gap(wrapper,10);
        card.addView(artwork(map,16),new LinearLayout.LayoutParams(dp(60),dp(60)));
        LinearLayout description=column();description.setPadding(dp(12),0,dp(4),0);
        TextView name=text(title(map),16,incompatibility(map).isEmpty()?WHITE:warningColor());name.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));name.setMaxLines(2);name.setEllipsize(TextUtils.TruncateAt.END);description.addView(name);
        TextView author=text(artist(map),12,MUTED);author.setMaxLines(1);author.setEllipsize(TextUtils.TruncateAt.END);description.addView(author);gap(description,3);
        description.addView(text(local?"On phone \u00b7 ZIP":rating(map),11,local?GREEN:MUTED));
        String incompatible=incompatibility(map);if(!incompatible.isEmpty())description.addView(text(incompatible,11,warningColor()));
        description.setOnClickListener(v->details(map));card.addView(description,new LinearLayout.LayoutParams(0,-2,1));
        String id=map.optString("id");boolean busy=downloading.contains(id),saved=installed(map);
        ImageButton downloadButton=icon(saved?R.drawable.ic_check:R.drawable.ic_download,busy?"Downloading":saved?"Downloaded to phone":"Download "+title(map),v->{if(saved)message("Already in your phone library");else download(map);});
        downloadButton.setEnabled(!busy);downloadButton.setAlpha(busy?.4f:1f);downloadButton.setColorFilter(saved?GREEN:MUTED);card.addView(downloadButton);
        card.addView(previewButton(map));
        card.addView(icon(R.drawable.ic_more,"Map actions",v->dialog().setTitle(title(map)).setItems(local?new String[]{"Map details","Delete phone download"}:new String[]{"Map details","Download to phone"},(d,w)->{if(w==0)details(map);else if(local)delete(map);else download(map);}).show()));
        return wrapper;
    }

    private ImageButton previewButton(JSONObject map){
        ImageButton button=icon(R.drawable.ic_play,"Preview "+title(map),v->preview(map));
        button.setTag("preview:"+map.optString("id"));button.setTooltipText(title(map));button.setBackground(ripple(GREEN,18));button.setColorFilter(BG);
        updatePreviewButton(button);return button;
    }
    private void updatePreviewButton(ImageButton button){
        String id=((String)button.getTag()).substring(8);boolean current=playback.matches(id);
        boolean pending=current&&playback.phase==PreviewState.Phase.LOADING;
        boolean playing=current&&playback.phase==PreviewState.Phase.PLAYING;
        button.setImageResource(pending?R.drawable.ic_close:playing?R.drawable.ic_pause:R.drawable.ic_play);
        String action=pending?"Cancel loading preview":playing?"Pause preview":current?"Resume preview":"Play preview";
        button.setContentDescription(action+": "+button.getTooltipText());
    }
    private void syncPreviewButtons(View view){
        if(ended||view==null)return;
        if(view instanceof ImageButton&&view.getTag() instanceof String&&((String)view.getTag()).startsWith("preview:"))updatePreviewButton((ImageButton)view);
        if(view instanceof ViewGroup){ViewGroup group=(ViewGroup)view;for(int i=0;i<group.getChildCount();i++)syncPreviewButtons(group.getChildAt(i));}
    }

    static boolean visibleSong(View view,String id){
        if(view.getVisibility()!=View.VISIBLE)return false;
        if(("song:"+id).equals(view.getTag())&&view.getGlobalVisibleRect(new Rect()))return true;
        if(view instanceof ViewGroup){ViewGroup group=(ViewGroup)view;for(int i=0;i<group.getChildCount();i++)if(visibleSong(group.getChildAt(i),id))return true;}
        return false;
    }

    private String audioSummary(JSONObject report){
        String codec=report.optString("audio_codec");if(codec.equals("unchanged"))return "Existing song retained (not recompressed)";
        return (codec.equals("vorbis")?(report.optString("audio_quality","original").equals("original")?"Original compressed Vorbis":"Re-encoded Vorbis: "+qualityLabel(report.optString("audio_quality"))):"PCM fallback: "+report.optString("audio_fallback_reason","normalized audio"))
            +(report.optLong("bundle_bytes")>0?String.format(Locale.ROOT," · Bundle %.2f MB",report.optLong("bundle_bytes")/1000000.0):"");
    }

    private void consoleCover(ImageView view,JSONObject song){
        String host=consoleCatalog.optString("host"),port=consoleCatalog.optString("port");
        if(song.optInt("cover_bytes")<=0)return;
        String key=UUID.nameUUIDFromBytes((host+":"+port+":"+song.optString("id")+":"+song.optString("cover_fnv")+":"+song.optInt("cover_bytes")).getBytes(StandardCharsets.UTF_8)).toString();
        view.setTag(key);Bitmap cached=covers.get(key);if(cached!=null){view.setImageBitmap(cached);return;}
        view.post(()->{if(ended||!view.isAttachedToWindow())return;images.execute(()->{try{
            File folder=new File(getCacheDir(),"ps4-covers"),file=new File(folder,key+".png");
            Bitmap bitmap=file.isFile()?BitmapFactory.decodeFile(file.getAbsolutePath()):null;
            if(bitmap==null){
                byte[] data=ConversionRuntime.consoleCover(getApplicationContext(),Core.privateAddress(host),Core.port(port),song);
                BitmapFactory.Options options=new BitmapFactory.Options();options.inJustDecodeBounds=true;BitmapFactory.decodeByteArray(data,0,data.length,options);
                if(options.outWidth!=512||options.outHeight!=512)return;
                options.inJustDecodeBounds=false;options.inSampleSize=2;bitmap=BitmapFactory.decodeByteArray(data,0,data.length,options);
                if(bitmap!=null&&(folder.isDirectory()||folder.mkdirs())){
                    File[] old=folder.listFiles();if(old!=null&&old.length>=64){Arrays.sort(old,Comparator.comparingLong(File::lastModified));for(int i=0;i<=old.length-64;i++)old[i].delete();}
                    File pending=File.createTempFile("cover-",".tmp",folder);
                    try(FileOutputStream out=new FileOutputStream(pending)){bitmap.compress(Bitmap.CompressFormat.PNG,100,out);}finally{if(!pending.renameTo(file))pending.delete();}
                }
            }
            if(bitmap!=null){final Bitmap shown=bitmap;covers.put(key,shown);ui(()->{if(key.equals(view.getTag()))view.setImageBitmap(shown);});}
        }catch(Exception | LinkageError ignored){/* Offline/changed cover leaves a harmless placeholder. */}});});
    }

    private void cover(ImageView view,String url){
        if(url.isEmpty())return;view.setTag(url);Bitmap cached=covers.get(url);if(cached!=null){view.setImageBitmap(cached);return;}
        view.post(()->{if(ended||!view.isAttachedToWindow())return;images.execute(()->{try{byte[] data=Core.bytes(url,4L*1024*1024);BitmapFactory.Options options=new BitmapFactory.Options();options.inJustDecodeBounds=true;BitmapFactory.decodeByteArray(data,0,data.length,options);if(options.outWidth<=0||options.outHeight<=0||options.outWidth>8192||options.outHeight>8192)return;options.inJustDecodeBounds=false;options.inSampleSize=1;while(options.outWidth/options.inSampleSize>256||options.outHeight/options.inSampleSize>256)options.inSampleSize*=2;Bitmap bitmap=BitmapFactory.decodeByteArray(data,0,data.length,options);if(bitmap!=null){covers.put(url,bitmap);ui(()->{if(url.equals(view.getTag()))view.setImageBitmap(bitmap);});}}catch(Exception ignored){/* Cover failure never blocks the map list. */}});});
    }

    private void load(boolean reset){
        if(loading && !reset)return;
        if(reset){stopPreview();page=0;maps.clear();}else page++;
        final int ticket=++generation,requested=page;final String q=query,sort=order;final boolean byId=searchById;
        prefs.edit().putString("query",q).apply();loading=true;render();
        work.execute(()->{try{JSONArray docs=searchMaps(q,requested,sort,byId);ArrayList<JSONObject> result=new ArrayList<>();for(int i=0;i<docs.length();i++){JSONObject map=docs.optJSONObject(i);if(map!=null&&Core.validId(map.optString("id")))result.add(map);}ui(()->{if(ticket!=generation)return;loading=false;Set<String> ids=new HashSet<>();for(JSONObject map:maps)ids.add(map.optString("id"));for(JSONObject map:result)if(ids.add(map.optString("id")))maps.add(map);if(tab==0)render();if(result.isEmpty()&&tab==0)message("No more maps for this search");});}catch(Exception e){ui(()->{if(ticket!=generation)return;loading=false;if(!reset)page=Math.max(0,page-1);if(tab==0)render();if(status!=null&&tab==0)status.setText("Could not load BeatSaver. Tap Refresh to retry.");message(e.getMessage());});}});
    }

    static JSONArray searchMaps(String q,int page,String sort,boolean byId) throws Exception {
        if(byId){
            if(q.isEmpty()||page>0)return new JSONArray();
            if(!Core.validId(q))throw new IOException("Enter a hexadecimal BeatSaver ID, e.g. 25975");
            try{
                JSONObject map=new JSONObject(new String(Core.bytes("https://api.beatsaver.com/maps/id/"+q.toLowerCase(Locale.ROOT),2L*1024*1024),StandardCharsets.UTF_8));
                if(!map.optString("id").equalsIgnoreCase(q))throw new IOException("Unexpected BeatSaver map ID");
                return new JSONArray().put(map);
            }catch(Core.HttpError error){if(error.status!=404)throw error;return new JSONArray();}
        }
        JSONObject response=new JSONObject(new String(Core.bytes("https://api.beatsaver.com/search/text/"+page+"?q="+URLEncoder.encode(q,"UTF-8")+"&sortOrder="+sort,2L*1024*1024),StandardCharsets.UTF_8));
        JSONArray docs=response.optJSONArray("docs");if(docs==null)throw new IOException("Unexpected BeatSaver response");return docs;
    }

    private void filters(){
        String[] labels={"Featured / curated","Latest","Best rated","Search relevance"},values={"Curated","Latest","Rating","Relevance"};
        int selected=Arrays.asList(values).indexOf(order);
        AlertDialog dialog=dialog().setTitle("Sort maps").setSingleChoiceItems(labels,selected,(d,w)->{order=values[w];d.dismiss();load(true);}).setNegativeButton("Close",null).create();
        dialog.setOnShowListener(d->dialog.getWindow().setBackgroundDrawable(shape(BAR,28)));dialog.show();
    }

    static JSONArray catalogSongs(JSONObject catalog,String host,String port){
        try{if(!Core.privateAddress(host).equals(catalog.optString("host"))||Core.port(port)!=catalog.optInt("port",-1))return null;}catch(IOException invalid){return null;}
        JSONObject snapshot=catalog.optJSONObject("snapshot");return snapshot==null?null:snapshot.optJSONArray("songs");
    }

    private void rememberConsole(String host,int port,JSONObject snapshot){
        try{consoleCatalog=new JSONObject().put("host",host).put("port",String.valueOf(port)).put("read_at",System.currentTimeMillis()).put("snapshot",snapshot);prefs.edit().putString("consoleCatalog",consoleCatalog.toString()).apply();}catch(JSONException error){message("Could not save the console catalog");}
    }

    private View consoleSongCard(JSONObject song){
        LinearLayout wrapper=column();wrapper.setPadding(dp(16),0,dp(16),0);
        LinearLayout card=row();card.setPadding(dp(14),dp(16),dp(14),dp(16));card.setBackground(shape(BAR,26));wrapper.addView(card);gap(wrapper,10);
        ImageView art=new ImageView(this);art.setImageResource(R.drawable.icon);art.setContentDescription("Cover for "+song.optString("title"));art.setScaleType(ImageView.ScaleType.CENTER_CROP);art.setBackground(shape(BAR,12));art.setClipToOutline(true);card.addView(art,new LinearLayout.LayoutParams(dp(48),dp(48)));consoleCover(art,song);
        LinearLayout description=column();description.setPadding(dp(14),0,0,0);
        TextView name=text(song.optString("title","Untitled"),16,WHITE);name.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));name.setMaxLines(2);description.addView(name);
        description.addView(text(song.optString("author","Unknown artist"),12,MUTED));description.addView(text("On PS4 · OrBeats",11,GREEN));card.addView(description,new LinearLayout.LayoutParams(0,-2,1));
        card.setOnClickListener(v->dialog().setTitle(song.optString("title")).setMessage(song.optString("author")+"\n\nInstalled in the PS4 OrBeats pack. This catalog entry is not a phone download.\n\nLevel ID: "+song.optString("id")).setNegativeButton("Close",null).setPositiveButton("Remove from PS4",(d,w)->manageConsole(null,song)).show());return wrapper;
    }

    private void renderLibrary(){
        body.addView(text("Your library",27,WHITE));gap(body,12);
        LinearLayout sources=row();Button remote=button("On PS4",v->{showPs4Library=true;stopPreview();render();});Button phone=button("On phone",v->{showPs4Library=false;stopPreview();render();});
        remote.setBackground(ripple(showPs4Library?GREEN:TONAL,24));remote.setTextColor(showPs4Library?BG:GREEN);remote.setSelected(showPs4Library);
        phone.setBackground(ripple(showPs4Library?TONAL:GREEN,24));phone.setTextColor(showPs4Library?GREEN:BG);phone.setSelected(!showPs4Library);
        sources.addView(remote,new LinearLayout.LayoutParams(0,-2,1));sources.addView(phone,new LinearLayout.LayoutParams(0,-2,1));body.addView(sources);gap(body,12);
        if(showPs4Library){
            JSONArray songs=catalogSongs(consoleCatalog,prefs.getString("host",""),prefs.getString("port","2121"));
            String summary=songs==null?"Read your PS4's existing OrBeats pack to display its songs here.":songs.length()+" songs on PS4 · Last read "+java.text.DateFormat.getDateTimeInstance(java.text.DateFormat.SHORT,java.text.DateFormat.SHORT).format(new Date(consoleCatalog.optLong("read_at")))+"\nSaved catalog, not a live connection. Refresh after console changes.";
            body.addView(text(summary,14,MUTED));gap(body,12);body.addView(button(preparingSong?"Console operation in progress…":"Refresh PS4 library",v->consoleCheck(null)));gap(body,12);
            if(songs!=null){for(int i=0;i<songs.length();i++){JSONObject song=songs.optJSONObject(i);if(song!=null)displayed.add(song);}if(songs.length()==0)body.addView(text("Your PS4 OrBeats pack is empty.",17,MUTED));}
            return;
        }
        body.addView(text("Phone downloads. Install a song into your existing PS4 OrBeats pack, or prepare it locally.",14,MUTED));gap(body,16);
        File[] directories=library.listFiles();int count=0;
        if(directories!=null){Arrays.sort(directories,Comparator.comparing(File::getName));for(File folder:directories){if(!Core.validId(folder.getName()))continue;File json=new File(folder,"map.json");if(!json.isFile()||!new File(folder,"map.zip").isFile()||json.length()>2*1024*1024)continue;try{JSONObject map=new JSONObject(new String(java.nio.file.Files.readAllBytes(json.toPath()),StandardCharsets.UTF_8));if(!folder.equals(songDir(map)))continue;displayed.add(map);count++;}catch(Exception ignored){}}}
        if(count==0)body.addView(text("No downloaded songs yet. Find one in Discover and tap its download arrow.",17,MUTED));
    }

    private void download(JSONObject map){
        final String id=map.optString("id");final File target=songDir(map);if(target==null){message("Invalid map ID");return;}if(installed(map)){message("Already downloaded");return;}if(!downloading.add(id))return;message("Downloading "+title(map)+". Keep OrBeats open.");render();
        work.execute(()->{File stage=new File(library,".pending-"+UUID.randomUUID());boolean committed=false;try{if(!stage.mkdir())throw new IOException("Cannot create download staging folder");File zip=new File(stage,"map.zip");try(OutputStream output=new FileOutputStream(zip)){Core.fetch(version(map).optString("downloadURL"),output,Core.MAX_ZIP);}Core.validateZip(zip);try(FileOutputStream output=new FileOutputStream(new File(stage,"map.json"))){output.write(map.toString().getBytes(StandardCharsets.UTF_8));output.getFD().sync();}if(Thread.currentThread().isInterrupted())throw new InterruptedIOException("Cancelled");if(target.exists()||!stage.renameTo(target))throw new IOException("Could not publish download; existing library left unchanged");committed=true;ui(()->message("Downloaded to phone: "+title(map)));}catch(Exception e){ui(()->message("Download failed: "+e.getMessage()));}finally{if(!committed){new File(stage,"map.zip").delete();new File(stage,"map.json").delete();stage.delete();}downloading.remove(id);ui(()->{if(tab!=2)render();});}});
    }

    private void delete(JSONObject map){dialog().setTitle("Delete phone download?").setMessage(title(map)+"\n\nThis removes only the phone copy. Nothing on your PS4 is changed.").setNegativeButton("Cancel",null).setPositiveButton("Delete",(d,w)->{File folder=songDir(map);if(folder==null)return;boolean ok=true;for(String name:new String[]{"map.zip","map.json"}){File f=new File(folder,name);if(f.exists()&&!f.delete())ok=false;}folder.delete();if(!ok)message("Could not delete all download files");render();}).show();}

    static String mapSize(JSONObject map){return mapSize(version(map).optLong("size",0));}
    static String mapSize(long size){
        return size>0?String.format(Locale.ROOT,"BeatSaver download: %.2f MB (installed size varies)",size/1000000.0):"BeatSaver download size unavailable (installed size varies)";
    }

    private String audioQuality(){return prefs.getString("audioQuality","original");}
    private String qualityLabel(String quality){return quality.equals("balanced")?"Balanced (lossy)":quality.equals("small")?"Small (lossy)":"Original (no re-encoding)";}
    private void qualitySettings(){
        String[] values={"original","balanced","small"};String[] labels={"Original — preserve source quality","Balanced — lossy Vorbis, smaller files","Small — lossy Vorbis, smallest files"};
        int selected=Arrays.asList(values).indexOf(audioQuality());
        dialog().setTitle("Audio quality for new preparations / installs").setSingleChoiceItems(labels,Math.max(0,selected),(dialog,which)->{prefs.edit().putString("audioQuality",values[which]).apply();dialog.dismiss();render();}).setNegativeButton("Cancel",null).show();
    }

    private void details(JSONObject map){
        JSONObject meta=metadata(map);JSONObject ver=version(map);StringBuilder detail=new StringBuilder(artist(map)+"\nMapper: "+meta.optString("levelAuthorName","Unknown")+"\nMap ID: "+map.optString("id")+"\n"+rating(map)+"\n"+mapSize(map)+"\n\nDifficulties:\n");JSONArray diffs=ver.optJSONArray("diffs");if(diffs!=null)for(int i=0;i<diffs.length();i++){JSONObject diff=diffs.optJSONObject(i);if(diff!=null)detail.append(diff.optString("characteristic")).append(" \u00b7 ").append(diff.optString("difficulty")).append("\n");}detail.append("\n").append(incompatibility(map).isEmpty()?"Compatibility has not been fully checked.":incompatibility(map));detail.append("\nInstall to PS4 adds this song to your existing OrBeats pack, after a read-only check and explicit confirmation. Beat Saber must be fully closed. Load song only prepares it locally.");AlertDialog dialog=dialog().setTitle(title(map)).setMessage(detail).setPositiveButton(installed(map)?"Load song":"Download",(d,w)->{if(installed(map))loadSong(map);else download(map);}).setNeutralButton(installed(map)?"Install to PS4":null,(d,w)->consoleCheck(map)).setNegativeButton("Close",null).create();
        File folder=songDir(map);File archive=folder==null?null:new File(folder,"map.zip");
        if(archive!=null&&archive.isFile())dialog.setMessage(detail.toString().replace(mapSize(map),mapSize(archive.length())));
        else if(ver.optLong("size",0)<=0){
            final String description=detail.toString();
            work.execute(()->{try{long size=Core.downloadSize(ver.optString("downloadURL"));if(size>0)ui(()->{if(dialog.isShowing()){dialog.setMessage(description.replace(mapSize(map),mapSize(size)));try{ver.put("size",size);}catch(JSONException ignored){}}});}catch(IOException ignored){/* A missing HEAD size must not block details or download. */}});
        }
        dialog.show();
    }

    private void preview(JSONObject map){preview(map,null);}
    private void preview(JSONObject map,File local){
        if(playback.matches(map.optString("id"))){
            if(playback.phase==PreviewState.Phase.LOADING){stopPreview();return;}
            try{
                if(playback.phase==PreviewState.Phase.PLAYING){player.pause();playback.pause();}
                else{player.start();playback.resume();}
                syncPreviewButtons(root);
            }catch(IllegalStateException e){stopPreview();message("Preview could not be played");}
            return;
        }
        stopPreview();final int ticket=playback.begin(map.optString("id"));syncPreviewButtons(root);
        work.execute(()->{
            File file=null;
            try{
                file=File.createTempFile("orbeats-preview-",local==null?".mp3":".wav",getCacheDir());
                if(local!=null)java.nio.file.Files.copy(local.toPath(),file.toPath(),java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                else try(OutputStream output=new FileOutputStream(file)){Core.fetch(version(map).optString("previewURL"),output,16L*1024*1024);}
                final File ready=file;
                runOnUiThread(()->{
                    if(ended||isFinishing()||!playback.current(ticket)){ready.delete();return;}
                    previewFile=ready;
                    try{
                        player=new MediaPlayer();player.setDataSource(ready.getAbsolutePath());
                        player.setOnPreparedListener(p->{
                            if(!playback.current(ticket)||p!=player)return;
                            try{p.start();playback.prepared(ticket);syncPreviewButtons(root);}
                            catch(IllegalStateException e){stopPreview();message("Preview could not start");}
                        });
                        player.setOnCompletionListener(p->{if(playback.current(ticket)&&p==player)stopPreview();});
                        player.setOnErrorListener((p,what,extra)->{if(playback.current(ticket)&&p==player){stopPreview();message("Preview could not be played");}return true;});
                        player.prepareAsync();
                    }catch(Exception e){stopPreview();message("Preview unavailable: "+e.getMessage());}
                });
            }catch(Exception e){if(file!=null)file.delete();ui(()->{if(playback.current(ticket)){stopPreview();message("Preview unavailable: "+e.getMessage());}});}
        });
    }
    private void stopPreview(){playback.stop();if(player!=null){player.release();player=null;}if(previewFile!=null){previewFile.delete();previewFile=null;}syncPreviewButtons(root);}

    private void settings(){
        body.addView(text("Console & settings",26,WHITE));gap(body,12);body.addView(text("Save your PS4's local address and read its existing OrBeats plugin/library over anonymous GoldHEN FTP. Close Beat Saber first. The check is read-only; installation requires a separate confirmation.",15,MUTED));gap(body,12);
        EditText host=new EditText(this);host.setTextColor(WHITE);host.setHintTextColor(MUTED);host.setSingleLine(true);host.setHint("PS4 IP, e.g. 192.168.1.100");host.setText(prefs.getString("host",""));host.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_URI);host.setContentDescription("Console local IPv4 address");body.addView(host);
        EditText port=new EditText(this);port.setTextColor(WHITE);port.setHintTextColor(MUTED);port.setSingleLine(true);port.setHint("FTP port");port.setText(prefs.getString("port","2121"));port.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);port.setContentDescription("GoldHEN FTP port");body.addView(port);
        for(EditText field:new EditText[]{host,port}){field.setBackground(shape(BAR,16));field.setPadding(dp(16),0,dp(16),0);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,dp(56));p.setMargins(0,0,0,dp(12));field.setLayoutParams(p);}
        Button test=button("Save & test console connection",v->{try{final String address=Core.privateAddress(host.getText().toString());final int number=Core.port(port.getText().toString());prefs.edit().putString("host",address).putString("port",String.valueOf(number)).apply();consoleCheck(null);}catch(IOException e){message(e.getMessage());}});body.addView(test);gap(body,12);body.addView(button("How to link your console (?)",v->tutorial()));gap(body,12);body.addView(button("Stop audio preview",v->stopPreview()));gap(body,24);
        Switch mode=new Switch(this);mode.setText("Light mode");mode.setTextSize(16);mode.setTextColor(WHITE);mode.setMinHeight(dp(56));mode.setPadding(dp(16),0,dp(16),0);mode.setBackground(shape(BAR,16));mode.setChecked(lightMode);body.addView(mode,new LinearLayout.LayoutParams(-1,-2));
        mode.setOnCheckedChangeListener((v,checked)->{
            lightMode=checked;prefs.edit().putBoolean("lightMode",checked).putString("host",host.getText().toString()).putString("port",port.getText().toString()).apply();
            int position=list.getFirstVisiblePosition();View first=list.getChildAt(0);int offset=first==null?0:first.getTop();
            buildUi();list.setSelectionFromTop(position,offset);
        });gap(body,20);
        body.addView(button("Audio quality: "+qualityLabel(audioQuality()),v->qualitySettings()));gap(body,12);
        body.addView(text("Smaller options re-encode audio and lose some quality. Bitrate/file size varies. Downloads and existing PS4 songs stay unchanged.",14,MUTED));gap(body,12);
        body.addView(button("Conversion template (optional)",v->templateSettings()));gap(body,12);
        body.addView(button("Install/update OrBeats",v->manageConsole("main",null)));gap(body,12);
        body.addView(button("Install/update Extras",v->manageConsole("extras",null)));gap(body,12);
        body.addView(button("Open-source notices",v->notices()));gap(body,20);
        body.addView(text("OrBeats Android 0.1.9\nUnofficial standalone companion\n\nBeatSaver supplies maps, covers and previews. No BeatSaver account or localhost server is required.\n\nDownloads remain in this app's private phone storage; uninstalling removes them. Keep the app open during downloads. Library → song → Load song prepares supported V2/V3/V4 audio/charts. A compatible template enables local PS4 bundle output. Install to PS4 uses the existing OrBeats pack and preserves previous entries. Library → On PS4 shows cached covers and offers confirmed removal. Settings installs/enables official OrBeats or Extras while preserving unrelated plugins. Supported Vorbis audio keeps its original compression; other audio uses PCM fallback. Keep OrBeats open and Beat Saber closed throughout installation; then restart the game.",14,MUTED));
    }

    private void consoleCheck(JSONObject map){
        if(preparingSong){message("Wait for the current song/console operation");return;}
        final String host;final int port;
        try{host=Core.privateAddress(prefs.getString("host",""));port=Core.port(prefs.getString("port","2121"));}
        catch(IOException error){message("Save the console address in Settings first: "+error.getMessage());return;}
        final boolean libraryView=map==null&&tab==1;
        preparingSong=true;message("Reading OrBeats library — no console writes…");
        android.content.Context app=getApplicationContext();
        work.execute(()->{
            try{
                JSONObject snapshot=ConversionRuntime.consoleStatus(app,host,port);
                ui(()->{
                    preparingSong=false;rememberConsole(host,port,snapshot);
                    if(tab==1)render();
                    JSONArray songs=snapshot.optJSONArray("songs");int count=songs==null?0:songs.length();
                    StringBuilder summary=new StringBuilder(host+":"+port+"\nOrBeats: "+count+" / "+snapshot.optInt("max_songs")+" songs\n\n");
                    if(map==null){
                        if(songs!=null)for(int i=0;i<songs.length();i++){JSONObject song=songs.optJSONObject(i);if(song!=null)summary.append(song.optString("title")).append("\n");}
                        summary.append("\nRead-only check. No console files changed.");
                        if(libraryView){showPs4Library=true;render();message("PS4 library refreshed: "+count+" songs");}
                        else dialog().setTitle("PS4 OrBeats library").setMessage(summary).setPositiveButton("View Library",(d,w)->{showPs4Library=true;tab=1;render();}).setNegativeButton("Close",null).show();
                    }else{
                        final String quality=audioQuality();
                        summary.append("Install: ").append(title(map)).append("\nAudio: ").append(qualityLabel(quality)).append("\n\nThis will upload this song and update the existing OrBeats library index. Existing songs and OST/DLC are preserved. The template is obtained from an installed song automatically; an empty library needs a retained/local template.\n\nCUSA12878 patch 2.04 only. Keep Beat Saber fully CLOSED and this app open. Use trusted LAN FTP only. Do not run another companion. A lost connection may require manual recovery; do not delete an install lock blindly.\n\nAfter success, restart Beat Saber and select OrBeats. PCM playback was tested; compressed/selected-quality playback still needs hardware verification.");
                        dialog().setTitle("Confirm PS4 installation").setMessage(summary).setNegativeButton("Cancel",null)
                            .setPositiveButton("Install to this PS4",(d,w)->installSong(map,host,port,snapshot,quality)).show();
                    }
                });
            }catch(Exception | LinkageError error){ui(()->{preparingSong=false;dialog().setTitle("Console/library check failed").setMessage(error.toString()+"\n\nThis was a read-only check; no console writes were requested. The specific reason above can concern FTP or the OrBeats setup/library—not necessarily a connection problem. Do not delete backups, locks or recovery files to bypass a refusal.").setPositiveButton("Close",null).show();});}
        });
    }

    private void installSong(JSONObject map,String host,int port,JSONObject confirmed,String quality){
        if(preparingSong){message("Wait for the current operation");return;}
        File folder=songDir(map);if(folder==null||!installed(map)){message("Download this song first");return;}
        preparingSong=true;stopPreview();getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        installProgress=dialog().setTitle("Installing into OrBeats…")
            .setMessage(title(map)+"\n\nPreparing audio/charts and verifying uploads may take several minutes. Keep this app open, Beat Saber fully CLOSED and FTP running. Do not interrupt a transaction or run another companion.")
            .setCancelable(false).show();
        android.content.Context app=getApplicationContext();
        work.execute(()->{
            try{
                JSONObject result=ConversionRuntime.install(app,host,port,new File(folder,"map.zip"),version(map).optString("hash"),templateFile(),confirmed,quality);
                JSONObject refreshed=null;try{refreshed=ConversionRuntime.consoleStatus(app,host,port);}catch(Exception | LinkageError ignored){/* A refresh failure must not turn a committed install into an error. */}
                final JSONObject catalog=refreshed;
                ui(()->{preparingSong=false;if(catalog!=null)rememberConsole(host,port,catalog);if(tab==1)render();if(installProgress!=null){installProgress.dismiss();installProgress=null;}getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);dialog().setTitle(result.optBoolean("already_present")?"Already in OrBeats":"Added to OrBeats")
                    .setMessage(result.optString("title")+"\n"+result.optInt("count")+" installed songs\n"+audioSummary(result)+"\n\nLaunch/restart Beat Saber and select OrBeats. Check the new song and your older songs. Local recovery records are retained in app-private storage.").setPositiveButton("Close",null).show();});
            }catch(Exception | LinkageError error){ui(()->{preparingSong=false;rememberIncompatibility(map,error);if(installProgress!=null){installProgress.dismiss();installProgress=null;}getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);dialog().setTitle("Installation stopped — inspect before retry")
                .setMessage(error.toString()+"\n\nKeep Beat Saber CLOSED. Some staged/immutable files may remain. The upstream installer protects publication of the library and retains recovery records; a dropped connection/process may need manual recovery. Do not clear app data or remove a lock blindly. Plugin/config/OST files were not intentionally changed.").setPositiveButton("Close",null).show();});}
        });
    }

    private File templateFile(){return new File(getFilesDir(),"conversion-template.bundle");}

    private void manageConsole(String plugin,JSONObject song){
        if(preparingSong){message("Wait for the current console/conversion operation");return;}
        final String host;final int port;
        try{host=Core.privateAddress(prefs.getString("host",""));port=Core.port(prefs.getString("port","2121"));}
        catch(IOException error){message(error.getMessage());return;}
        if(plugin!=null){confirmManagement(host,port,plugin,null,null);return;}
        preparingSong=true;message("Reading the current PS4 library before removal\u2026");
        work.execute(()->{
            try{
                JSONObject snapshot=ConversionRuntime.consoleStatus(getApplicationContext(),host,port);
                JSONArray songs=snapshot.getJSONArray("songs");JSONObject current=null;
                for(int i=0;i<songs.length();i++)if(songs.getJSONObject(i).optString("id").equals(song.optString("id")))current=songs.getJSONObject(i);
                if(current==null)throw new IOException("This song is no longer installed; refresh the PS4 library");
                final JSONObject selected=current;
                ui(()->{preparingSong=false;rememberConsole(host,port,snapshot);confirmManagement(host,port,null,selected,snapshot);});
            }catch(Exception | LinkageError error){ui(()->{preparingSong=false;dialog().setTitle("Cannot confirm removal").setMessage(error.toString()+"\n\nThis was a read-only check. No removal was requested.").setPositiveButton("Close",null).show();});}
        });
    }

    private void confirmManagement(String host,int port,String plugin,JSONObject song,JSONObject snapshot){
        boolean removing=plugin==null;
        String title=removing?"Remove from PS4?":"Install/update "+(plugin.equals("main")?"OrBeats":"Extras")+"?";
        String explanation=removing?song.optString("title")+"\n\nRemove this song from the PS4 OrBeats pack. Other songs and phone downloads stay unchanged. Removing the last song retains its conversion template.":"Download the official stable "+(plugin.equals("main")?"OrBeats":"Extras")+" plugin, upload it and enable its entry for CUSA12878 in plugins.ini. Existing songs and other plugin entries are preserved. Extras requires OrBeats to be installed first.";
        dialog().setTitle(title).setMessage(explanation+"\n\nPS4: "+host+":"+port+"\nKeep Beat Saber CLOSED, FTP enabled and this app open. Restart the game after success.")
            .setNegativeButton("Cancel",null).setPositiveButton(removing?"Remove":"Install & enable",(d,w)->writeManagement(host,port,plugin,song,snapshot)).show();
    }

    private void writeManagement(String host,int port,String plugin,JSONObject song,JSONObject confirmed){
        if(preparingSong){message("Wait for the current operation");return;}
        preparingSong=true;getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        installProgress=dialog().setTitle(plugin==null?"Removing from OrBeats":"Installing official plugin").setMessage("Keep Beat Saber closed and this app open. Do not run another installer. Writing and verifying console files\u2026").setCancelable(false).create();installProgress.show();
        work.execute(()->{
            try{
                JSONObject result=plugin==null?ConversionRuntime.remove(getApplicationContext(),host,port,song.getString("id"),confirmed):ConversionRuntime.installPlugin(getApplicationContext(),host,port,plugin);
                JSONObject refreshed=null;String refreshWarning="";
                try{refreshed=ConversionRuntime.consoleStatus(getApplicationContext(),host,port);}catch(Exception | LinkageError error){refreshWarning="\n\nThe operation completed, but refreshing the library failed: "+error.toString();}
                final JSONObject snapshot=refreshed;final String warning=refreshWarning;
                ui(()->{preparingSong=false;if(installProgress!=null){installProgress.dismiss();installProgress=null;}getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    if(snapshot!=null)rememberConsole(host,port,snapshot);else{consoleCatalog=null;prefs.edit().remove("consoleCatalog").apply();}
                    render();String pending=result.optJSONArray("cleanup_pending")==null||result.optJSONArray("cleanup_pending").length()==0?"":"\n\nCleanup pending: "+result.optJSONArray("cleanup_pending").toString();
                    dialog().setTitle(plugin==null?"Song removed from PS4":"Plugin installed and enabled").setMessage("Restart Beat Saber to apply the change."+pending+warning).setPositiveButton("Close",null).show();});
            }catch(Exception | LinkageError error){ui(()->{preparingSong=false;if(installProgress!=null){installProgress.dismiss();installProgress=null;}getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                consoleCatalog=null;prefs.edit().remove("consoleCatalog").apply();render();
                dialog().setTitle("Console operation stopped \u2014 inspect before retry").setMessage(error.toString()+"\n\nFiles may already have been committed or may need recovery. Keep Beat Saber closed. Do not clear app data or delete locks/backups. Recovery records are retained in the app's private files.").setPositiveButton("Close",null).show();});}
        });
    }

    private void loadSong(JSONObject map){
        if(preparingSong){message("Song preparation is already running");return;}
        File folder=songDir(map);if(folder==null||!installed(map)){message("Download this song first");return;}
        final String quality=audioQuality();
        preparingSong=true;message("Loading "+title(map)+". Keep OrBeats open…");
        android.content.Context app=getApplicationContext();
        work.execute(()->{
            try{
                JSONObject report=ConversionRuntime.prepare(app,new File(folder,"map.zip"),version(map).optString("hash"),templateFile(),quality);
                ui(()->{preparingSong=false;showLoadedSong(map,report);});
            }catch(Exception | LinkageError e){ui(()->{preparingSong=false;rememberIncompatibility(map,e);render();dialog().setTitle("Song could not be loaded").setMessage(e.toString()+"\n\nThe downloaded ZIP is unchanged. No console files changed.").setPositiveButton("Close",null).show();});}
        });
    }

    private void showLoadedSong(JSONObject map,JSONObject report){
        boolean bundle=report.optBoolean("bundle_created");
        String summary=report.optString("title")+"\n"+audioSummary(report)+"\nInfo version: "+report.optString("info_version")+"\nDuration: "+Math.round(report.optDouble("duration_seconds"))+" seconds\n\nNotes by difficulty:\n"+report.optJSONObject("note_counts")+"\n\n"+(bundle?"PS4 bundle, cover and preview created and reopened/validated locally. This does not prove console playback.":"Charts/audio and cover/preview prepared. No PS4 bundle yet: select a compatible template in Settings, then load again.")+"\n\nSkipped charts: "+report.optJSONArray("skipped_difficulties")+"\nNothing was uploaded to your console.";
        dialog().setTitle("Song loaded").setMessage(summary)
            .setPositiveButton("Play prepared preview",(d,w)->{stopPreview();preview(map,new File(report.optString("preview")));})
            .setNeutralButton("Export preparation",(d,w)->{
                exportSource=new File(report.optString("output_directory"),"prepared-song.zip");
                Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("application/zip");
                intent.putExtra(Intent.EXTRA_TITLE,"OrBeats-"+map.optString("id")+"-prepared.zip");
                try{startActivityForResult(intent,72);}catch(ActivityNotFoundException e){exportSource=null;message("No document picker available");}
            }).setNegativeButton("Close",null).show();
    }

    private void templateSettings(){
        if(preparingSong){message("Wait for song preparation to finish");return;}
        dialog().setTitle("Conversion template — optional")
            .setMessage("A compatible Beat Saber song bundle supplies the Unity layout for full PS4 output. Use a legal local copy from your own existing OrBeats setup. No game assets are included in this app.\n\nWithout a template you can still load songs, validate their charts/audio and play the prepared preview.\n\nCurrent: "+(templateFile().isFile()?"selected":"none"))
            .setPositiveButton("Choose bundle",(d,w)->{try{startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*"),71);}catch(ActivityNotFoundException e){message("No document picker available");}})
            .setNeutralButton("Remove selection",(d,w)->{if(templateFile().exists()&&!templateFile().delete())message("Could not remove template");else message("Template selection removed; downloaded songs unchanged");})
            .setNegativeButton("Close",null).show();
    }

    @Override protected void onSaveInstanceState(Bundle state){
        if(exportSource!=null)state.putString("exportSource",exportSource.getAbsolutePath());
        super.onSaveInstanceState(state);
    }

    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(result!=RESULT_OK||data==null||data.getData()==null){if(request==72)exportSource=null;return;}
        final android.net.Uri uri=data.getData();
        if(request==71){
            if(preparingSong){message("Wait for song preparation to finish");return;}
            preparingSong=true;
            work.execute(()->{
                File stage=new File(getFilesDir(),".template-"+UUID.randomUUID());
                try{
                    try(InputStream input=getContentResolver().openInputStream(uri);FileOutputStream output=new FileOutputStream(stage)){
                    if(input==null)throw new IOException("Cannot open template");
                    byte[] buffer=new byte[65536];long total=0;int n;
                    while((n=input.read(buffer))!=-1){if(Thread.currentThread().isInterrupted())throw new InterruptedIOException("Cancelled");total+=n;if(total>200000000)throw new IOException("Template exceeds200MB");output.write(buffer,0,n);}
                    if(total==0)throw new IOException("Empty template");output.getFD().sync();
                    }
                    ConversionRuntime.validateTemplate(getApplicationContext(),stage);
                    java.nio.file.Files.move(stage.toPath(),templateFile().toPath(),java.nio.file.StandardCopyOption.ATOMIC_MOVE,java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                    ui(()->message("Template selected. Load a song to validate compatibility."));
                }catch(Exception | LinkageError e){ui(()->message("Template selection failed; previous selection unchanged: "+e.getMessage()));}
                finally{stage.delete();ui(()->preparingSong=false);}
            });
        }else if(request==72){
            final File source=exportSource;exportSource=null;
            work.execute(()->{
                try{
                    File allowed=new File(getCacheDir(),"prepared-songs").getCanonicalFile();
                    if(source==null||!source.getCanonicalPath().startsWith(allowed.getPath()+File.separator)||!source.isFile())throw new IOException("Preparation expired; load the song again");
                    try(InputStream input=new FileInputStream(source);OutputStream output=getContentResolver().openOutputStream(uri,"w")){
                        if(output==null)throw new IOException("Cannot create export");byte[] buffer=new byte[65536];int n;
                        while((n=input.read(buffer))!=-1){if(Thread.currentThread().isInterrupted())throw new InterruptedIOException("Cancelled");output.write(buffer,0,n);}
                    }
                    ui(()->message("Preparation exported. Nothing installed on the console."));
                }catch(Exception e){ui(()->message("Export failed: "+e.getMessage()+". A partial destination file may remain."));}
            });
        }
    }

    private void notices(){
        try(InputStream in=getAssets().open("NOTICES.txt")){
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int n;
            while((n=in.read(buffer))!=-1){if(bytes.size()+n>512*1024)throw new IOException("Notices too large");bytes.write(buffer,0,n);}
            dialog().setTitle("Open-source notices").setMessage(new String(bytes.toByteArray(),StandardCharsets.UTF_8)).setPositiveButton("Close",null).show();
        }catch(IOException e){message("Cannot read notices: "+e.getMessage());}
    }

    private void tutorial(){dialog().setTitle("Link your PS4").setMessage("1. Connect your phone and PS4 to the same local network.\n\n2. Enable GoldHEN's FTP server on the PS4. Keep FTP restricted to your trusted network; do not expose it to the Internet.\n\n3. Find the PS4's IP address in its network/status information. GoldHEN FTP usually uses port 2121.\n\n4. Open OrBeats Settings, enter that address and port, then tap Save & test console connection. Close Beat Saber first. This reads/verifies the existing OrBeats library without writes.\n\n5. Full OrBeats installs require CUSA12878 patch 2.04, its plugin and Beat Saber fully closed before writes.\n\nRead PS4 OrBeats library checks the current plugin/index without writes. To add a downloaded song, open its details → Install to PS4 → review and confirm. The existing library supplies the conversion template automatically when nonempty. Keep app open, game closed and FTP on; after success launch Beat Saber and select OrBeats. Settings has separate official OrBeats and Extras install/update buttons, each with confirmation. On PS4 song details allows confirmed removal; phone deletion stays separate. Red warnings identify known unsupported maps, but unmarked maps are not guaranteed compatible. Exported preparations are NOT installable packages.").setPositiveButton("Open settings",(d,w)->{tab=2;render();}).setNegativeButton("Close",null).show();}

    @Override protected void onStop(){stopPreview();super.onStop();}
    @Override protected void onDestroy(){ended=true;if(installProgress!=null){installProgress.dismiss();installProgress=null;}stopPreview();work.shutdownNow();images.shutdownNow();super.onDestroy();}
    private final class Logo extends View {
        final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        Logo(){super(MainActivity.this);setContentDescription("OrBeats logo");}
        @Override protected void onDraw(Canvas canvas){float s=Math.min(getWidth(),getHeight());paint.setColor(GREEN);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(s*.045f);canvas.drawCircle(s/2,s/2,s*.45f,paint);paint.setStrokeCap(Paint.Cap.ROUND);float[] heights={.16f,.42f,.61f,.42f,.16f};for(int i=0;i<5;i++){float x=s*(.24f+i*.13f),h=s*heights[i];canvas.drawLine(x,(s-h)/2,x,(s+h)/2,paint);}}
    }
}
