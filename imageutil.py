import urequests
import binascii
import png
from inkplate2 import Inkplate      

def extract_data(html_content):
    #Find start and end of the figure section
    figure_start = html_content.find('<figure class="image main">')
    figure_end = html_content.find('</figure>')
    figure_content = html_content[figure_start:figure_end]
    #Extracting Image Source
    img_src_start = figure_content.find('<img src="') + len('<img src="')
    img_src_end = figure_content.find('"', img_src_start)
    img_src = figure_content[img_src_start:img_src_end]
    #Extracting Caption
    caption_start = figure_content.find('<figcaption>') + len('<figcaption>')
    caption_end = figure_content.find('</figcaption>')
    caption = figure_content[caption_start:caption_end]
    return img_src, caption

def get_beer():
    url = "https://www.brewbunny.com/current-beer/"
    response = urequests.get(url)
    img_src, beer_name = extract_data(response.text)
    response.close()
    img_src = 'https://www.brewbunny.com' + img_src
    return beer_name, img_src

def get_filename_from_url(url):
    return url.split("/")[-1]

def calculate_crc(filename):
    with open(filename, 'rb') as f:
        file_content = f.read()
    crc_val = binascii.crc32(file_content)
    return crc_val

def download_image(url):
    filename = get_filename_from_url(url)
    response = urequests.get(url)
    with open(filename, 'wb') as f:
        f.write(response.content)
    response.close()
    return filename

def display_image(display, png_file_path):
    display.clearDisplay()
    display.startWrite()
    png_reader = png.Reader(filename=png_file_path)
    w, h, pixels, meta = png_reader.asRGB()
    print(f"Display {png_file_path} {w}x{h}")
    row=0
    for rowdata in pixels:
        col = 0
        for i in range(0, len(rowdata), 3):
            rgb = rowdata[i:i+3]
            r = rgb[0]
            g = rgb[1]
            b = rgb[2]
            if b < 100 and g < 100:
                if r < 120:
                    display.writePixel(col, row, Inkplate.BLACK)
                else:
                    display.writePixel(col, row, Inkplate.RED)
            col = col + 1
        row = row + 1
    display.endWrite()
