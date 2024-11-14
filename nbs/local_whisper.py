from RealtimeSTT import AudioToTextRecorder

if __name__ == "__main__":
    device = "mps"
    with AudioToTextRecorder(model="base", language="pt", device="mps") as recorder:
        print("Transcription: ", recorder.text())
