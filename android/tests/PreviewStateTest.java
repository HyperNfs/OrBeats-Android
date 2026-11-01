package dev.orbeats.android;

public final class PreviewStateTest {
    private static int checks;
    private static void check(boolean ok) { checks++; if(!ok)throw new AssertionError("Preview check "+checks); }
    public static void main(String[] args) {
        PreviewState state=new PreviewState();
        check(state.phase==PreviewState.Phase.STOPPED);
        check(!state.matches("a"));check(!state.current(0));
        int first=state.begin("a");
        check(state.matches("a")&&!state.matches("b"));
        check(state.phase==PreviewState.Phase.LOADING&&state.current(first));
        state.pause();state.resume();check(state.phase==PreviewState.Phase.LOADING);
        check(state.prepared(first));check(state.phase==PreviewState.Phase.PLAYING);
        check(!state.prepared(first));
        state.pause();check(state.phase==PreviewState.Phase.PAUSED&&state.matches("a"));
        state.resume();check(state.phase==PreviewState.Phase.PLAYING);
        int second=state.begin("b");
        check(second!=first&&!state.current(first)&&state.current(second));
        check(!state.prepared(first)&&state.phase==PreviewState.Phase.LOADING);
        check(state.prepared(second));
        state.stop();check(state.phase==PreviewState.Phase.STOPPED&&!state.matches("b"));
        check(!state.current(second)&&!state.prepared(second));
        state.pause();state.resume();check(state.phase==PreviewState.Phase.STOPPED);
        int cancelled=state.begin("a");state.stop();
        check(!state.prepared(cancelled)&&state.mapId.isEmpty());
        int newest=state.begin("a");
        check(!state.current(cancelled)&&state.current(newest));
        check(state.prepared(newest));state.stop();
        check(!state.current(newest)&&state.phase==PreviewState.Phase.STOPPED);
        System.out.println("PASS: "+checks+" preview loading/cancel/play/pause/resume/completion/stale-token state checks (not MediaPlayer device execution)");
    }
}
