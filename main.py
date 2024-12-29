import sdcard
import machine
import uos
import urequests
import jpegdec
from presto import Presto
from time import time, sleep
import network
import secrets

# Initialize Presto
presto = Presto(ambient_light=True)
display = presto.display
WIDTH, HEIGHT = display.get_bounds()

jpeg = jpegdec.JPEG(display)

# Directory on SD card to save images
SD_DIR = "/sd/gallery"

# Prompts for image generation
prompts = [
    "synthwave style new retro wave city scapes at night",
    "vaporwave aesthetic city skyline with neon lights",
    "cyberpunk futuristic metropolis with glowing buildings",
    "retrofuturistic space station with vibrant colors",
    "neon-lit arcade scene with futuristic machines",
    "80s-style synthwave desert landscape with neon sun",
    "futuristic train station with glowing lights",
    "nighttime beach with neon palm trees and synthwave style",
    "cyberpunk city streets with vibrant holograms",
    "retro wave sci-fi space with glowing planets and stars"
]

# Colors for text rendering
DARK_BLUE = display.create_pen(10, 30, 80)  # Dark blue background
WHITE = display.create_pen(255, 255, 255)
BLACK = display.create_pen(0, 0, 0)  # Pre-created black pen

def draw_background():
    """
    Draws a solid dark blue background.
    """
    display.set_pen(DARK_BLUE)
    display.clear()
    presto.update()

def display_text_on_screen(message):
    """
    Displays a text message on the Presto screen with a solid dark blue background.
    """
    draw_background()  # Set the solid dark blue background
    display.set_pen(WHITE)  # Text color
    display.text(message, 10, 85, WIDTH, 2)  # Font scale 2
    presto.update()
    sleep(1)

def generate_unique_prompt(base_prompt):
    """
    Appends a timestamp to the base prompt to ensure each prompt is unique.
    """
    timestamp = int(time())
    return f"{base_prompt} {timestamp}"

def fetch_image(prompt):
    """
    Fetches an image from Pollinations API for the given prompt.
    """
    url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
    print(f"Fetching image for prompt: '{prompt}'...")
    try:
        response = urequests.get(url)
        if response.status_code == 200:
            print("Image fetched successfully!")
            return response.content
        else:
            print(f"Error fetching image. Status code: {response.status_code}. Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None

def save_image_to_sd(prompt, image_data):
    """
    Saves the fetched image to the SD card.
    """
    try:
        timestamp = int(time())
        filename = f"{prompt.replace(' ', '_')}_{timestamp}.jpg"
        filepath = f"{SD_DIR}/{filename}"
        
        with open(filepath, "wb") as f:
            f.write(image_data)
        print(f"Image saved to {filepath}")
        return filepath
    except OSError as e:
        print(f"Error saving image: {e}")
        return None

def fade_out_image(filepath):
    """
    Fades out the current image.
    """
    brightness_steps = [i / 10.0 for i in range(11)]
    step_delay = 1.5 / len(brightness_steps)

    display_image_on_layer(filepath, 0)

    for brightness in reversed(brightness_steps):
        presto.set_backlight(brightness)
        presto.update()
        sleep(step_delay)

    display.set_pen(BLACK)
    display.clear()
    presto.update()

def fade_in_image(filepath):
    """
    Fades in the new image.
    """
    brightness_steps = [i / 10.0 for i in range(11)]
    step_delay = 1.5 / len(brightness_steps)

    display_image_on_layer(filepath, 0)

    for brightness in brightness_steps:
        presto.set_backlight(brightness)
        presto.update()
        sleep(step_delay)

    presto.set_backlight(1.0)
    presto.update()

def display_image_on_layer(filepath, layer):
    """
    Displays an image on the specified layer of the Presto display.
    """
    try:
        display.set_layer(layer)
        jpeg.open_file(filepath)
        img_width, img_height = jpeg.get_width(), jpeg.get_height()
        scale = jpegdec.JPEG_SCALE_HALF if img_width > WIDTH or img_height > HEIGHT else jpegdec.JPEG_SCALE_FULL
        scaled_width = img_width // (2 if scale == jpegdec.JPEG_SCALE_HALF else 1)
        scaled_height = img_height // (2 if scale == jpegdec.JPEG_SCALE_HALF else 1)
        img_x = (WIDTH - scaled_width) // 2
        img_y = (HEIGHT - scaled_height) // 2
        jpeg.decode(img_x, img_y, scale, dither=True)
    except Exception as e:
        print(f"Error displaying image on layer {layer}: {e}")

def connect_to_wifi():
    """
    Connects to Wi-Fi and displays connection status on Presto display.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    display_text_on_screen("Connecting to Wi-Fi...")
    if not wlan.isconnected():
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        while not wlan.isconnected():
            sleep(1)
            display_text_on_screen("Connecting to Wi-Fi...")
    ip_address = wlan.ifconfig()[0]
    display_text_on_screen(f"Wi-Fi Connected\nIP: {ip_address}")
    print(f"\nConnected to Wi-Fi!\nIP Address: {ip_address}")

def mount_sd():
    """
    Mounts the SD card and displays status on Presto display.
    """
    try:
        display_text_on_screen("Initializing SD Card...")
        sd_spi = machine.SPI(0, 
                             sck=machine.Pin(34, machine.Pin.OUT), 
                             mosi=machine.Pin(35, machine.Pin.OUT), 
                             miso=machine.Pin(36, machine.Pin.OUT))
        sd = sdcard.SDCard(sd_spi, machine.Pin(39))
        uos.mount(sd, "/sd")
        display_text_on_screen("SD Card Mounted")
        print("SD card mounted successfully!")
    except Exception as e:
        display_text_on_screen("SD Card Mount Failed")
        print(f"Error mounting SD card: {e}")

def clear_gallery():
    """
    Deletes all files in the gallery directory and displays status.
    """
    try:
        display_text_on_screen("Clearing Gallery...")
        files = uos.listdir(SD_DIR)
        for file in files:
            filepath = f"{SD_DIR}/{file}"
            uos.remove(filepath)
            print(f"Deleted: {filepath}")
        display_text_on_screen("Gallery Cleared")
    except OSError as e:
        print(f"Error clearing gallery: {e}")

def endless_photo_viewer():
    """
    The main workflow of the photo viewer.
    """
    # Display startup messages
    connect_to_wifi()   # Display "Connecting to Wi-Fi"
    mount_sd()          # Display "Initializing SD Card"
    clear_gallery()     # Display "Clearing Gallery"

    prompt_index = 0
    prev_filepath = None
    first_image = True  # Flag to display "Fetching image" only for the first fetch

    while True:
        # Generate prompt for the next image
        base_prompt = prompts[prompt_index]
        unique_prompt = generate_unique_prompt(base_prompt)

        # Fetch and save the next image
        if first_image:
            display_text_on_screen("Fetching Image...")
            first_image = False  # Ensure this is only displayed once

        next_image_data = fetch_image(unique_prompt)
        if next_image_data:
            next_filepath = save_image_to_sd(unique_prompt, next_image_data)

            if next_filepath:
                # Fade out the current image if it exists
                if prev_filepath:
                    fade_out_image(prev_filepath)

                # Fade in the new image
                fade_in_image(next_filepath)

                # Delete the previous image
                if prev_filepath:
                    try:
                        uos.remove(prev_filepath)
                        print(f"Deleted: {prev_filepath}")
                    except OSError as e:
                        print(f"Error deleting file {prev_filepath}: {e}")

                # Update the previous file path
                prev_filepath = next_filepath

        # Move to the next prompt
        prompt_index = (prompt_index + 1) % len(prompts)
        sleep(7)

if __name__ == "__main__":
    endless_photo_viewer()

