package dev.orbeats.android;

/** Main-thread state, including cancellation of stale asynchronous previews. */
final class PreviewState {
    enum Phase { STOPPED, LOADING, PLAYING, PAUSED }
    String mapId = "";
    Phase phase = Phase.STOPPED;
    private int generation;

    int begin(String id) {
        generation++;
        mapId = id;
        phase = Phase.LOADING;
        return generation;
    }
    boolean current(int token) { return token == generation && phase != Phase.STOPPED; }
    boolean matches(String id) { return phase != Phase.STOPPED && mapId.equals(id); }
    boolean prepared(int token) {
        if (!current(token) || phase != Phase.LOADING) return false;
        phase = Phase.PLAYING;
        return true;
    }
    void pause() { if (phase == Phase.PLAYING) phase = Phase.PAUSED; }
    void resume() { if (phase == Phase.PAUSED) phase = Phase.PLAYING; }
    void stop() { generation++; mapId = ""; phase = Phase.STOPPED; }
}
