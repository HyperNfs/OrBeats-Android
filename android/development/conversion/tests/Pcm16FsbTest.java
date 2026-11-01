/* SPDX-License-Identifier: GPL-3.0-only */
package dev.orbeats.conversion;

import java.io.IOException;
import java.io.InterruptedIOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

public final class Pcm16FsbTest {
    private static int checks;
    private static void check(boolean ok) { if (!ok) throw new AssertionError("check " + checks); checks++; }
    private static byte[] wave(int frames, short peak) {
        ByteBuffer b = ByteBuffer.allocate(44 + frames * 4).order(ByteOrder.LITTLE_ENDIAN);
        b.putInt(0x46464952).putInt(b.capacity() - 8).putInt(0x45564157);
        b.putInt(0x20746d66).putInt(16).putShort((short) 1).putShort((short) 2);
        b.putInt(44100).putInt(176400).putShort((short) 4).putShort((short) 16);
        b.putInt(0x61746164).putInt(frames * 4);
        while (b.hasRemaining()) b.putShort(peak);
        return b.array();
    }
    private static void reject(Path dir, byte[] bytes) throws Exception {
        Path in = dir.resolve("bad.wav"), out = dir.resolve("bad.fsb");
        Files.write(in, bytes);
        try { Pcm16Fsb.convert(in, out); throw new AssertionError("accepted malformed input"); }
        catch (IOException expected) { check(!Files.exists(out)); }
    }
    public static void main(String[] args) throws Exception {
        if (args.length == 2) {
            System.out.println(Pcm16Fsb.convert(java.nio.file.Paths.get(args[0]), java.nio.file.Paths.get(args[1])));
            return;
        }
        Path dir = Files.createTempDirectory("orbeats-pcm-test-");
        try {
            Path in = dir.resolve("audio.wav"), out = dir.resolve("audio.fsb");
            Files.write(in, wave(44100, (short) 1000));
            check(Pcm16Fsb.convert(in, out) == 44100);
            byte[] bank = Files.readAllBytes(out);
            ByteBuffer h = ByteBuffer.wrap(bank).order(ByteOrder.LITTLE_ENDIAN);
            check(bank.length == 125 + 44100 * 4);
            check(h.getInt(0) == 0x35425346 && h.getInt(4) == 1 && h.getInt(8) == 1);
            check(h.getInt(12) == 65 && h.getInt(16) == 0 && h.getInt(20) == 44100 * 4);
            check(h.getInt(24) == 2 && h.getInt(28) == 1 && h.getInt(77) == 44100);
            check((h.getLong(60) >>> 34) == 44100);
            check(((h.getLong(60) >>> 1) & 15) == 8 && ((h.getLong(60) >>> 5) & 1) == 1);
            check(h.getShort(125) == 999); // Match upstream float32 -> int16 truncation.
            try { Pcm16Fsb.convert(in, out); throw new AssertionError("overwrote output"); }
            catch (IOException expected) { check(Arrays.equals(bank, Files.readAllBytes(out))); }
            try { Pcm16Fsb.convert(in, in); throw new AssertionError("overwrote input"); }
            catch (IOException expected) { check(Files.size(in) == 44 + 44100 * 4); }
            Files.delete(out);
            Files.write(in, wave(44100, Short.MIN_VALUE));
            Pcm16Fsb.convert(in, out);
            check(ByteBuffer.wrap(Files.readAllBytes(out)).order(ByteOrder.LITTLE_ENDIAN).getShort(125) == -32439);
            Files.delete(out);
            byte[] good = wave(44100, (short) 0);
            reject(dir, new byte[0]);
            reject(dir, Arrays.copyOf(good, good.length - 1));
            reject(dir, wave(44099, (short) 0));
            for (int[] mutation : new int[][] {{0,0}, {4,1}, {8,0}, {16,15}, {20,3}, {22,1}, {24,48000}, {28,1}, {32,2}, {34,24}, {36,0}, {40,-1}, {40,1}}) {
                byte[] bad = good.clone();
                if (mutation[0] == 20 || mutation[0] == 22 || mutation[0] == 32 || mutation[0] == 34)
                    ByteBuffer.wrap(bad).order(ByteOrder.LITTLE_ENDIAN).putShort(mutation[0], (short) mutation[1]);
                else ByteBuffer.wrap(bad).order(ByteOrder.LITTLE_ENDIAN).putInt(mutation[0], mutation[1]);
                reject(dir, bad);
            }
            Path link = dir.resolve("link.wav"), linkOut = dir.resolve("link.fsb");
            Files.createSymbolicLink(link, in);
            try { Pcm16Fsb.convert(link, linkOut); throw new AssertionError("followed input symlink"); }
            catch (IOException expected) { check(!Files.exists(linkOut)); }
            Files.delete(link);
            Files.createSymbolicLink(linkOut, in);
            try { Pcm16Fsb.convert(in, linkOut); throw new AssertionError("overwrote symlink"); }
            catch (IOException expected) { check(Files.isSymbolicLink(linkOut) && Files.size(in) == good.length); }
            Files.delete(linkOut);
            Thread.currentThread().interrupt();
            try { Pcm16Fsb.convert(in, out); throw new AssertionError("ignored cancellation"); }
            catch (InterruptedIOException expected) { check(!Files.exists(out)); }
            finally { Thread.interrupted(); }
            // A directory target must not be removed by failure cleanup.
            Files.createDirectory(out);
            try { Pcm16Fsb.convert(in, out); throw new AssertionError("overwrote directory"); }
            catch (IOException expected) { check(Files.isDirectory(out)); }
            Files.delete(out);
            System.out.println("PASS: " + checks + " PCM/RIFF/header/normalization/refusal/no-overwrite/cancellation checks (standalone harness, not Activity/UI)");
        } finally {
            try (java.util.stream.Stream<Path> files = Files.list(dir)) {
                for (Path file : (Iterable<Path>) files::iterator) Files.deleteIfExists(file);
            }
            Files.delete(dir);
        }
    }
}
