import base64
from io import BytesIO

from flask import Flask, request, jsonify
import requests
from rembg import remove
import os

app = Flask(__name__)
@app.route('/', methods=['GET'])
def home():
    return "Hello from the root route!"

@app.route('/test-route', methods=['GET'])
def test_route():
    return "Test route is working!"

# Endpoint to process images
@app.route('/process-images', methods=['POST'])
def process_images():
    # Expect a JSON payload with a key "image_urls"
    data = request.get_json()
    if not data or 'image_urls' not in data:
        return jsonify({'error': 'Please provide a list of image_urls in JSON.'}), 400

    image_urls = data['image_urls']
    
    # Check if number of images exceed limit
    if len(image_urls) > 50:
        return jsonify({'error': 'A maximum of 50 images is allowed.'}), 400

    processed_images = []
    
    for url in image_urls:
        try:
            # Download image from URL
            response = requests.get(url)
            if response.status_code != 200:
                processed_images.append({
                    'original_url': url,
                    'error': 'Failed to download image. HTTP Status: {}'.format(response.status_code)
                })
                continue

            # Read image bytes and process background removal
            input_image_bytes = BytesIO(response.content)
            output_image_bytes = remove(input_image_bytes.read())

            # Convert the output bytes back to an image file-like object
            output_buffer = BytesIO(output_image_bytes)

            # Encode processed image in base64
            processed_image_b64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')

            processed_images.append({
                'original_url': url,
                'processed_image_base64': processed_image_b64
            })
        except Exception as e:
            processed_images.append({
                'original_url': url,
                'error': str(e)
            })

    # Once all images are processed, forward the data to the n8n endpoint.
    # (Replace the URL below with your actual n8n webhook/endpoint URL)
    n8n_endpoint = 'https://primary-production-7f6d.up.railway.app/webhook-test/0207105a-af75-4564-a6f1-ab2f166fd682'
    try:
        n8n_response = requests.post(n8n_endpoint, json={'images': processed_images}, headers={'Content-Type': 'application/json'})
        if n8n_response.status_code != 200:
            return jsonify({
                'error': 'Failed to forward images to n8n. HTTP Status: {}'.format(n8n_response.status_code)
            }), 500
    except Exception as e:
        return jsonify({'error': 'Error forwarding to n8n: ' + str(e)}), 500

    return jsonify({
        'message': 'Images processed and forwarded to n8n successfully.',
        'results': processed_images
    }), 200

if __name__ == '__main__':
    # Get the assigned port from Railway, default to 5000 if not set
    port = int(os.environ.get("PORT", 8080))

    # Print statement for debugging (optional)
    print(f"🚀 Flask app starting on port {port}...")

    # Run Flask with the dynamically assigned port
    app.run(host='0.0.0.0', port=port)
