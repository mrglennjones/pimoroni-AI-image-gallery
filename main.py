import sdcard
import machine
import uos
import urequests
import jpegdec
from presto import Presto
from time import time, sleep
import network
import secrets  # Import Wi-Fi credentials

# Setup for Presto display with ambient lighting enabled
presto = Presto(ambient_light=True)
display = presto.display
WIDTH, HEIGHT = display.get_bounds()

# Initialize JPEG Decoder
j = jpegdec.JPEG(display)

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

# Choose full resolution (480x480) or scaled resolution for faster display
full_res = True # Set to False for scaled resolution (faster)

# Generate a unique prompt by appending a timestamp
def generate_unique_prompt(base_prompt):
    timestamp = int(time())
    return f"{base_prompt} {timestamp}"

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

        # Check if SD card is detected
        print("Initializing SD card...")
        uos.mount(sd, "/sd")
        print("SD card mounted successfully!")

        # Create the gallery directory if it doesn't exist
        if not SD_DIR in uos.listdir("/sd"):
            uos.mkdir(SD_DIR)
        print("Gallery directory ready!")
    except OSError as e:
        if "ENOENT" in str(e):
            print("No SD card detected! Please insert an SD card.")
        elif "EEXIST" in str(e):
            print("SD card already mounted.")
        else:
            print(f"Failed to mount SD card: {e}")

# Delete all images in the gallery folder
def clear_gallery():
    try:
        for file in uos.listdir(SD_DIR):
            filepath = f"{SD_DIR}/{file}"
            uos.remove(filepath)
            print(f"Deleted {filepath}")
        print("Gallery cleared.")
    except Exception as e:
        print(f"Error clearing gallery: {e}")

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

# Display image and dynamically adjust backlighting
# Display image and properly scale to fit 480x480
def display_image(filepath):
    try:
        # Open the JPEG file
        j.open_file(filepath)

        # Decode the JPEG at half scale (768x768 -> 384x384)
        scale = jpegdec.JPEG_SCALE_HALF
        img_width, img_height = j.get_width() // 2, j.get_height() // 2

        # Calculate centering for 384x384 image on 480x480 display
        img_x = (WIDTH - img_width) // 2
        img_y = (HEIGHT - img_height) // 2

        # Decode and display the image
        j.decode(img_x, img_y, scale, dither=True)

        # Ensure backlight is at full brightness
        presto.set_backlight(1.0)
        presto.update()

        print(f"Displayed image from {filepath} with proper scaling and centering.")
    except Exception as e:
        print(f"Error displaying image: {e}")


# Main workflow for endless photo viewer
def endless_photo_viewer():
    connect_to_wifi()  # Connect to Wi-Fi using secrets.py

    try:
        mount_sd()
    except Exception as e:
        print("Error initializing SD card. Exiting.")
        return  # Exit if the SD card isn't properly mounted

    prompt_index = 0  # Start with the first prompt

    while True:
        # Clear the gallery before fetching a new image
        try:
            clear_gallery()
        except Exception as e:
            print(f"Error clearing gallery: {e}")

        # Get the current prompt and cycle through the list
        base_prompt = prompts[prompt_index]
        unique_prompt = generate_unique_prompt(base_prompt)

        # Fetch image for the unique prompt
        image_data = fetch_image(unique_prompt)
        if image_data:
            # Save and display the image
            filepath = save_image_to_sd(unique_prompt, image_data)
            if filepath:
                display_image(filepath)
        else:
            print("Skipping due to fetch error.")

        # Move to the next prompt
        prompt_index = (prompt_index + 1) % len(prompts)

        # Wait for 7 seconds before displaying the next image
        sleep(7)

if __name__ == "__main__":
    endless_photo_viewer()

