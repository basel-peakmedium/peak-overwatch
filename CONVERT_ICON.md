# Convert App Icon SVG to PNG

## Option 1: Using Inkscape (Recommended)
```bash
# Install Inkscape if needed
# brew install inkscape (macOS)
# apt-get install inkscape (Ubuntu)

inkscape -w 1024 -h 1024 landing/app_icon.svg -o landing/app_icon.png
```

## Option 2: Using ImageMagick
```bash
# Install ImageMagick if needed
# brew install imagemagick (macOS)
# apt-get install imagemagick (Ubuntu)

convert -background none -density 300 landing/app_icon.svg -resize 1024x1024 landing/app_icon.png
```

## Option 3: Online Converters
1. Go to https://svgtopng.com/
2. Upload `landing/app_icon.svg`
3. Set size to 1024×1024
4. Download PNG

## Option 4: Using Python (requires cairosvg)
```bash
pip install cairosvg
python -c "import cairosvg; cairosvg.svg2png(url='landing/app_icon.svg', write_to='landing/app_icon.png', output_width=1024, output_height=1024)"
```

## Icon Design Details:
- **Size:** 1024×1024 pixels
- **Background:** Black (#000000)
- **Accent Colors:** Pink (#FF0050), Teal (#00F2EA)
- **Symbol:** Binoculars/eye representing "oversight"
- **Text:** "Peak Overwatch" with "TikTok Analytics" tagline

## For TikTok Developer Portal:
1. Convert SVG to PNG using any method above
2. Upload to TikTok Developer Portal as App Icon
3. File must be ≤5MB