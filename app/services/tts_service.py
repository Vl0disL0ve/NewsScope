import edge_tts
from pathlib import Path

class TTSService:
    async def text_to_speech(self, text: str, cluster_id: int, user_dir: str) -> str:
        user_path = Path(user_dir)
        user_path.mkdir(parents=True, exist_ok=True)
        
        filename = user_path / f"cluster_{cluster_id}.mp3"
        
        communicate = edge_tts.Communicate(text, "ru-RU-DmitryNeural")
        await communicate.save(str(filename))
        
        return str(filename)