"""CPU-only PyAV decoder using original presentation timestamps."""

from fractions import Fraction
import hashlib
import io
import shutil
from pathlib import Path

from .common import StudioError, uid

LIMITS = {"upload_bytes": 1024**3, "duration_s": 1800, "width": 3840, "height": 2160,
          "frames": 10000, "queue": 100, "payload_bytes": 1024**2,
          "input_frames": 7, "free_bytes": 2 * 1024**3}


def probe(path):
    import av
    try:
        with av.open(str(path), options={"protocol_whitelist": "file"}) as video:
            stream = video.streams.video[0]
            if "mp4" not in video.format.name or stream.codec_context.name != "h264":
                raise StudioError("FORMAT", "MP4/H.264 video required")
            duration = float(stream.duration * stream.time_base) if stream.duration else float(video.duration or 0) / 1e6
            if not 0 < duration <= LIMITS["duration_s"]:
                raise StudioError("DURATION", "Duration missing or over 30 minutes")
            w, h = stream.codec_context.width, stream.codec_context.height
            if not (0 < w <= LIMITS["width"] and 0 < h <= LIMITS["height"]):
                raise StudioError("DIMENSIONS", "Unsupported video dimensions")
            return {"duration_s": duration, "width": w, "height": h, "codec": "h264",
                    "decoder": "PyAV-" + av.__version__, "time_base": str(stream.time_base)}
    except StudioError:
        raise
    except Exception as exc:
        raise StudioError("DECODE", "Cannot read video") from exc


def extract(path, output_root, interval_s):
    import av
    if isinstance(interval_s, bool) or not isinstance(interval_s, (int, float)) or not 0.1 <= interval_s <= 60:
        raise StudioError("INTERVAL", "Sampling interval must be 0.1–60 seconds")
    info = probe(path)
    interval = Fraction(str(interval_s))
    records, last_emitted = [], None
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)

    def emit(frame):
        nonlocal last_emitted
        timestamp = Fraction(frame.pts) * frame.time_base
        if timestamp == last_emitted:
            return
        if len(records) >= LIMITS["frames"]:
            raise StudioError("FRAME_LIMIT", "More than 10000 sampled frames")
        if shutil.disk_usage(output).free < LIMITS["free_bytes"]:
            raise StudioError("DISK_FULL", "Insufficient decoder output space")
        picture = frame.to_image().convert("RGB")
        original_dimensions = list(picture.size)
        picture.thumbnail((1280, 1280))
        raw = picture.tobytes()
        encoded = io.BytesIO()
        picture.save(encoded, "PNG")
        asset_id = uid()
        (output / (asset_id + ".png")).write_bytes(encoded.getvalue())
        records.append({"frame_id": uid(), "asset_id": asset_id, "filename": asset_id + ".png",
                        "ordinal": len(records), "pts": frame.pts, "time_base": str(frame.time_base),
                        "timestamp_us": int(timestamp * 1000000), "dimensions": list(picture.size),
                        "original_dimensions": original_dimensions,
                        "pixel_sha256": hashlib.sha256(raw).hexdigest(),
                        "file_sha256": hashlib.sha256(encoded.getvalue()).hexdigest()})
        last_emitted = timestamp

    with av.open(str(path), options={"protocol_whitelist": "file"}) as container:
        stream = container.streams.video[0]
        stream.thread_type = "NONE"
        stream.codec_context.thread_count = 1
        previous, previous_time, boundary = None, None, None
        for frame in container.decode(stream):
            if frame.pts is None or frame.time_base is None:
                raise StudioError("PTS", "Frame lacks presentation timestamp")
            timestamp = Fraction(frame.pts) * frame.time_base
            if previous_time is not None and timestamp <= previous_time:
                raise StudioError("PTS", "Ambiguous or non-increasing timestamps")
            if previous is None:
                emit(frame)
                boundary = timestamp + interval
            else:
                while timestamp > boundary:
                    emit(previous)
                    boundary += interval
                if timestamp == boundary:
                    emit(frame)
                    boundary += interval
            previous, previous_time = frame, timestamp
        if previous is None:
            raise StudioError("EMPTY", "No video frames")
        emit(previous)
    return {"settings": {"interval_s": interval_s, "policy": "last-at-or-before-plus-endpoints-v1"},
            "probe": info, "frames": records}
