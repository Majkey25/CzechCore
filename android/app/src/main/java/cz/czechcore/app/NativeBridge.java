package cz.czechcore.app;

final class NativeBridge {
    static {
        System.loadLibrary("czechcore_jni");
    }

    private NativeBridge() {}

    static native String[] correct(String modelPath, String[] tokens);
}
