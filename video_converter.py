import os
import subprocess
import logging
import imageio_ffmpeg

logger = logging.getLogger(__name__)


def convert_to_video_note(input_path: str, output_path: str, max_duration: int = 60) -> bool:
    """
    Istalgan to'rtburchak yoki standart videoni Telegram Video Note (dumaloq video)
    talablariga mos holatda (1:1 kvadrat, 384x384, H.264/AAC, max 60 soniya) o'giradi.

    :param input_path: Asl video fayl manzili
    :param output_path: Dumaloq formatga o'tkazilgan video saqlanadigan manzil
    :param max_duration: Maksimal davomiylik (Telegram talabi bo'yicha 60 soniya)
    :return: Muvaffaqiyatli bo'lsa True, aks holda False
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Universal kvadrat qilib qirqish va 384x384 ga o'lchamlash
    filter_complex = "crop=min(iw\\,ih):min(iw\\,ih),scale=384:384"

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", input_path,
        "-t", str(max_duration),
        "-vf", filter_complex,
        "-c:v", "libx264",
        "-preset", "ultrafast",  # Maksimal tezlikda konvertatsiya qilish
        "-crf", "26",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-threads", "0",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"FFmpeg xatoligi (kod {res.returncode}): {res.stderr}")
            return False

        return os.path.exists(output_path) and os.path.getsize(output_path) > 0

    except Exception as e:
        logger.exception(f"Video konvertatsiyasida xatolik yuz berdi: {e}")
        return False
