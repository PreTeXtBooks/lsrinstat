#!/bin/bash
# Generate images for PreTeXt book from R scripts

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BOOKDOWN_SCRIPTS="$SCRIPT_DIR/bookdown/scripts"
BOOKDOWN_IMG="$SCRIPT_DIR/bookdown/img"
PRETEXT_ASSETS="$SCRIPT_DIR/pretext/generated-assets"

echo "Generating images for PreTeXt book..."

# Create the generated-assets directory if it doesn't exist
mkdir -p "$PRETEXT_ASSETS"

# Check if R is installed
if ! command -v Rscript &> /dev/null; then
    echo "Error: R is not installed. Please install R to generate images."
    exit 1
fi

# Check if ImageMagick's convert is installed for EPS to PNG conversion
if ! command -v convert &> /dev/null; then
    echo "Warning: ImageMagick 'convert' not found. Will try to copy existing PNG files only."
    CONVERT_AVAILABLE=false
else
    CONVERT_AVAILABLE=true
fi

# Function to run R script and handle errors
run_r_script() {
    local script_name="$1"
    local script_path="$BOOKDOWN_SCRIPTS/$script_name"
    
    if [ -f "$script_path" ]; then
        echo "Running $script_name..."
        cd "$BOOKDOWN_SCRIPTS"
        Rscript "$script_name" || echo "Warning: $script_name had errors, continuing..."
        cd "$SCRIPT_DIR"
    else
        echo "Warning: $script_path not found, skipping..."
    fi
}

# Run the R image generation scripts
echo "Generating images from R scripts..."
run_r_script "graphicsImages.R"
run_r_script "descriptiveImages.R"
run_r_script "regressionImages.R"
run_r_script "probabilityImages.R"
run_r_script "estimationImages.R"
run_r_script "nhstImages.R"
run_r_script "ttestImages.R"
run_r_script "anovaImages.R"
run_r_script "chisquareImages.R"
run_r_script "factorialAnovaImages.R"

# Convert EPS files to PNG and copy to generated-assets
echo "Converting and copying images to generated-assets..."

if [ "$CONVERT_AVAILABLE" = true ]; then
    # Find all EPS files and convert them to PNG
    find "$BOOKDOWN_IMG" -name "*.eps" -type f | while read eps_file; do
        # Get the base filename without path and extension
        base_name=$(basename "$eps_file" .eps)
        # Get the relative directory structure
        rel_dir=$(dirname "${eps_file#$BOOKDOWN_IMG/}")
        
        # Create target directory
        target_dir="$PRETEXT_ASSETS"
        mkdir -p "$target_dir"
        
        # Convert EPS to PNG
        png_file="$target_dir/${base_name}.png"
        
        # Use convert with good quality settings
        convert -density 300 "$eps_file" -quality 90 "$png_file" 2>/dev/null || {
            echo "Warning: Failed to convert $eps_file"
        }
        
        if [ -f "$png_file" ]; then
            echo "  Created: ${base_name}.png"
        fi
    done
fi

# Also copy any existing PNG files from bookdown/img to generated-assets
find "$BOOKDOWN_IMG" -name "*.png" -type f | while read png_file; do
    base_name=$(basename "$png_file")
    cp "$png_file" "$PRETEXT_ASSETS/" 2>/dev/null || true
    echo "  Copied: $base_name"
done

echo ""
echo "Image generation complete!"
echo "Generated images are in: $PRETEXT_ASSETS"
echo "Total images: $(find "$PRETEXT_ASSETS" -name "*.png" | wc -l)"
