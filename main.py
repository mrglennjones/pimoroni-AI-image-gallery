import sdcard
import machine
import uos
import urequests
import jpegdec
from presto import Presto
from time import time, sleep
import network
import secrets

# Initialize Presto with ambient lighting enabled
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

# Generate a unique prompt
def generate_unique_prompt(base_prompt):
    """
    Appends a timestamp to the base prompt to ensure each prompt is unique.
    """
    timestamp = int(time())
    return f"{base_prompt} {timestamp}"

# Delete all files in the gallery directory
def clear_gallery():
    try:
        files = uos.listdir(SD_DIR)
        for file in files:
            filepath = f"{SD_DIR}/{file}"
            uos.remove(filepath)
            print(f"Deleted: {filepath}")
        print("Gallery cleared.")
    except OSError as e:
        print(f"Error clearing gallery: {e}")

# Overlapping fade-out and fade-in
def fade_between_images(prev_filepath, next_filepath):
    # Brightness steps
    brightness_steps = [i / 10.0 for i in range(11)]  # [0.0, 0.1, ..., 1.0]
    fade_duration = 1.5  # Total fade time in seconds
    step_delay = fade_duration / len(brightness_steps)  # Time per step

    # Load both images on separate layers
    display_image_on_layer(prev_filepath, 0)
    display_image_on_layer(next_filepath, 1)

    # Start with both layers visible
    display.set_layer(0)  # Show the previous image
    display.set_layer(1)  # Show the next image
    display.update()

    # Perform the fade
    for step in range(len(brightness_steps)):
        brightness = brightness_steps[step]  # Incremental brightness

        # Gradually adjust backlight brightness
        presto.set_backlight(brightness)
        presto.update()
        sleep(step_delay)

    # Finalize the transition by showing only the next image
    display.set_layer(1)  # Keep the next image visible
    display.set_layer(0)  # Hide the previous image
    presto.set_backlight(1.0)  # Ensure the backlight is fully on

    # Delete the previous image file
    try:
        if prev_filepath:
            uos.remove(prev_filepath)
            print(f"Deleted previous image: {prev_filepath}")
    except OSError as e:
        print(f"Error deleting previous image: {e}")

# Main photo viewer workflow
def endless_photo_viewer():
    connect_to_wifi()
    mount_sd()
    clear_gallery()  # Clear gallery at startup

    prompt_index = 0
    prev_filepath = None

    while True:
        # Generate prompt
        base_prompt = prompts[prompt_index]
        unique_prompt = generate_unique_prompt(base_prompt)

        # Fetch image
        image_data = fetch_image(unique_prompt)
        if image_data:
            next_filepath = save_image_to_sd(unique_prompt, image_data)
            if next_filepath:
                if prev_filepath:
                    fade_between_images(prev_filepath, next_filepath)
                else:
                    # First image, display without fading
                    display_image_on_layer(next_filepath, 0)
                    presto.set_backlight(1.0)  # Ensure backlight is fully on
                    presto.update()
                prev_filepath = next_filepath

        prompt_index = (prompt_index + 1) % len(prompts)
        sleep(7)

# Connect to Wi-Fi
def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Connecting to Wi-Fi network '{secrets.WIFI_SSID}'...")
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        while not wlan.isconnected():
            sleep(1)
            print(".", end="")
    print("\nConnected to Wi-Fi!")
    print(f"IP Address: {wlan.ifconfig()[0]}")

# Mount SD card
def mount_sd():
    try:
        # Initialize SD card
        sd_spi = machine.SPI(0, 
                             sck=machine.Pin(34, machine.Pin.OUT), 
                             mosi=machine.Pin(35, machine.Pin.OUT), 
                             miso=machine.Pin(36, machine.Pin.OUT))
        sd = sdcard.SDCard(sd_spi, machine.Pin(39))
        uos.mount(sd, "/sd")
    except Exception as e:
        print(f"Error mounting SD card: {e}")

# Fetch image from Pollinations API
def fetch_image(prompt):
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

# Save image to SD card
def save_image_to_sd(prompt, image_data):
    try:
        # Use a unique filename with timestamp
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

# Display an image on a specific layer
def display_image_on_layer(filepath, layer):
    try:
        # Set the active layer
        display.set_layer(layer)
        
        # Open and decode the JPEG file
        jpeg.open_file(filepath)
        
        # Get image dimensions and calculate scaling
        img_width, img_height = jpeg.get_width(), jpeg.get_height()
        scale = jpegdec.JPEG_SCALE_HALF if img_width > WIDTH or img_height > HEIGHT else jpegdec.JPEG_SCALE_FULL
        scaled_width = img_width // (2 if scale == jpegdec.JPEG_SCALE_HALF else 1)
        scaled_height = img_height // (2 if scale == jpegdec.JPEG_SCALE_HALF else 1)
        img_x = (WIDTH - scaled_width) // 2
        img_y = (HEIGHT - scaled_height) // 2
        
        # Decode and render the image
        jpeg.decode(img_x, img_y, scale, dither=True)
    except Exception as e:
        print(f"Error displaying image on layer {layer}: {e}")

if __name__ == "__main__":
    endless_photo_viewer()

