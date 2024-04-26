"""Main file for the Jarvis project"""
import os
from os import PathLike
from time import time
import asyncio
from typing import Union

from dotenv import load_dotenv
import openai
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
    SpeakOptions,
)
import pygame
from pygame import mixer

from record import speech_to_text

# Load API keys
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# Initialize APIs
gpt_client = openai.Client(api_key=OPENAI_API_KEY)
deepgram = DeepgramClient(DEEPGRAM_API_KEY)
# mixer is a pygame module for playing audio
mixer.init()

# Change the context if you want to change Jarvis' personality
context = "You are Jarvis, Tony's AI virtual assistant from Marvel Cinematic Universe. You are witty and full of personality. Your answers should be limited to 1-2 short sentences. You should reference things from the MCU as much as possible"
conversation = {"Conversation": []}
RECORDING_PATH = "audio/recording.wav"
RESPONSE_PATH = "audio/response.wav"

def request_gpt(prompt: str) -> str:
    """
    Send a prompt to the GPT-3 API and return the response.

    Args:
        - state: The current state of the app.
        - prompt: The prompt to send to the API.

    Returns:
        The response from the API.
    """
    response = gpt_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"{prompt}",
            }
        ],
        model="gpt-4-turbo",
    )
    return response.choices[0].message.content


async def transcribe(
    file_name: Union[Union[str, bytes, PathLike[str], PathLike[bytes]], int]
):
    """
    Transcribe audio using Deepgram API.

    Args:
        - file_name: The name of the file to transcribe.

    Returns:
        The response from the API.
    """
    try:
        with open(file_name, "rb") as file:
            buffer_data = file.read()

        payload: FileSource = {
            "buffer": buffer_data,
        }
        # Configure Deepgram options for audio analysis
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
        )
        
        # Call the transcribe_file method with the text payload and options
        response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
        # uncomment to view raw response
        # print(response.to_json(indent=4))
        return response["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception as e:
        print(f"Exception: {e}")



def log(log: str):
    """
    Print and write to status.txt
    """
    print(log)
    with open("status.txt", "w") as f:
        f.write(log)


if __name__ == "__main__":
    while True:
        # Record audio
        log("Listening...")
        speech_to_text()
        log("Done listening")

        # Transcribe audio
        current_time = time()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        words = loop.run_until_complete(transcribe(RECORDING_PATH))
        # Record conversation in the text file
        with open("conv.txt", "a") as f:
            f.write(f"{words}\n")
        transcription_time = time() - current_time
        log(f"Finished transcribing in {transcription_time:.2f} seconds.")

        # Get response from GPT-3
        current_time = time()
        context += f"\nTony: {words}\nJarvis: "
        response = request_gpt(context)
        context += response
        gpt_time = time() - current_time
        log(f"Finished generating response in {gpt_time:.2f} seconds.")

        # Convert response to audio
        current_time = time()
        SPEAK_OPTIONS = {"text": response}
        # Configure Aura options
        options = SpeakOptions(
            model="aura-helios-en",
            encoding="linear16",
            container="wav"
        )
        # Call the save method on the speak property
        audio = deepgram.speak.v("1").save(RESPONSE_PATH, SPEAK_OPTIONS, options)

        audio_time = time() - current_time
        log(f"Finished generating audio in {audio_time:.2f} seconds.")

        # Play response
        log("Speaking...")
        sound = mixer.Sound("audio/response.wav")
        # Add response as a new line to conv.txt
        with open("conv.txt", "a") as f:
            f.write(f"{response}\n")
        sound.play()
        pygame.time.wait(int(sound.get_length() * 1000))
        print(f"\n --- USER: {words}\n --- JARVIS: {response}\n")
