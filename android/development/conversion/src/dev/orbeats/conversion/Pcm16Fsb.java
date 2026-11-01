/* SPDX-License-Identifier: GPL-3.0-only
 * PCM fallback port of Wkrotik/OrBeats hevag_encoder.py, commit
 * 098897736e089107704ec1633daff8922087fcc8. See development/conversion/README.md.
 */
package dev.orbeats.conversion;

import java.io.EOFException;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/** Offline PCM16 bank only: NOT a Unity bundle or an installable song. */
// shortcut: PCM16 stereo/44.1 kHz WAV only; add decoding/resampling for BeatSaver audio.
public strictfp final class Pcm16Fsb {
    private static final long MAX_PCM = 600L * 44100 * 4;
    private Pcm16Fsb() {}

    /** New caller-owned staging output only. Refuses overwrite; removes failed output. */
    public static long convert(Path input, Path output) throws IOException {
        if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Conversion cancelled");
        if (!Files.isRegularFile(input, LinkOption.NOFOLLOW_LINKS))
            throw new IOException("WAV input must be a regular file, not a symlink");
        boolean created = false, complete = false;
        try (FileChannel source = FileChannel.open(input, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            long size = source.size();
            if (size < 44 || size > MAX_PCM + 1024 * 1024)
                throw new IOException("WAV outside input size bound");
            ByteBuffer header = read(source, 12);
            if (header.getInt(0) != 0x46464952 || header.getInt(8) != 0x45564157 ||
                    Integer.toUnsignedLong(header.getInt(4)) + 8 != size)
                throw new IOException("Expected an exact RIFF/WAVE file");
            boolean format = false;
            long dataOffset = -1, dataBytes = -1;
            int chunks = 0;
            while (source.position() < size) {
                if (++chunks > 256 || size - source.position() < 8)
                    throw new IOException("Invalid or excessive WAV chunks");
                ByteBuffer chunk = read(source, 8);
                int kind = chunk.getInt(0);
                long length = Integer.toUnsignedLong(chunk.getInt(4));
                long start = source.position(), end = start + length + (length & 1);
                if (end > size) throw new IOException("Truncated WAV chunk");
                if (kind == 0x20746d66) { // fmt
                    if (format || dataOffset >= 0 || (length != 16 && length != 18))
                        throw new IOException("Ambiguous/unsupported WAV format chunk");
                    ByteBuffer f = read(source, (int) length);
                    if (f.getShort(0) != 1 || f.getShort(2) != 2 || f.getInt(4) != 44100 ||
                            f.getInt(8) != 176400 || f.getShort(12) != 4 || f.getShort(14) != 16 ||
                            (length == 18 && f.getShort(16) != 0))
                        throw new IOException("Requires PCM16 stereo 44100 Hz; no implicit resampling");
                    format = true;
                } else if (kind == 0x61746164) { // data
                    if (!format || dataOffset >= 0 || length % 4 != 0 || length < 44100 * 4 || length > MAX_PCM)
                        throw new IOException("Requires one complete data chunk, 1..600 seconds");
                    dataOffset = start;
                    dataBytes = length;
                }
                source.position(end);
            }
            if (!format || dataOffset < 0) throw new IOException("Missing WAV format or data");
            byte[] buffer = new byte[65536];
            MessageDigest first = sha256(), second = sha256();
            source.position(dataOffset);
            int peak = 0;
            long remaining = dataBytes;
            while (remaining > 0) {
                int count = (int) Math.min(buffer.length, remaining);
                readFully(source, ByteBuffer.wrap(buffer, 0, count));
                first.update(buffer, 0, count);
                for (int i = 0; i < count; i += 2)
                    peak = Math.max(peak, Math.abs((int) sample(buffer, i)));
                remaining -= count;
            }
            // Match upstream's NumPy2 float32 normalization, including truncation.
            boolean attenuate = peak / 32768f > 0.99f;
            float gain = attenuate ? 0.99f / (peak / 32768f) : 1f;
            long frames = dataBytes / 4;
            try (OutputStream sink = Files.newOutputStream(output, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
                created = true;
                ByteBuffer fsb = ByteBuffer.allocate(125).order(ByteOrder.LITTLE_ENDIAN);
                fsb.putInt(0, 0x35425346).putInt(4, 1).putInt(8, 1).putInt(12, 65);
                fsb.putInt(20, (int) dataBytes).putInt(24, 2).putInt(28, 1);
                fsb.putLong(60, 49L | (frames << 34));
                fsb.putInt(68, 1 | (1 << 1) | (1 << 25));
                fsb.put(72, (byte) 2);
                fsb.putInt(73, (4 << 1) | (2 << 25)).putInt(77, 44100);
                sink.write(fsb.array());
                source.position(dataOffset);
                remaining = dataBytes;
                while (remaining > 0) {
                    int count = (int) Math.min(buffer.length, remaining);
                    readFully(source, ByteBuffer.wrap(buffer, 0, count));
                    second.update(buffer, 0, count);
                    for (int i = 0; i < count; i += 2) {
                        float value = sample(buffer, i) / 32768f;
                        if (attenuate) value *= gain;
                        short normalized = (short) (value * 32767f);
                        buffer[i] = (byte) normalized;
                        buffer[i + 1] = (byte) (normalized >> 8);
                    }
                    sink.write(buffer, 0, count);
                    remaining -= count;
                }
                if (source.size() != size || !MessageDigest.isEqual(first.digest(), second.digest()))
                    throw new IOException("WAV changed during conversion");
            }
            complete = true;
            return frames;
        } finally {
            if (created && !complete) Files.deleteIfExists(output);
        }
    }

    private static short sample(byte[] bytes, int offset) {
        return (short) ((bytes[offset] & 255) | (bytes[offset + 1] << 8));
    }

    private static ByteBuffer read(FileChannel source, int length) throws IOException {
        ByteBuffer result = ByteBuffer.allocate(length).order(ByteOrder.LITTLE_ENDIAN);
        readFully(source, result);
        result.flip();
        return result;
    }

    private static void readFully(FileChannel source, ByteBuffer buffer) throws IOException {
        while (buffer.hasRemaining()) {
            if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Conversion cancelled");
            if (source.read(buffer) < 0) throw new EOFException("Truncated WAV");
        }
    }

    private static MessageDigest sha256() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
}
