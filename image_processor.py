from PIL import Image

def process_image(image, params):
    action = params.get('action', 'resize')
    
    if action == 'resize':
        return image.resize(
            (params['width'], params['height']),
            Image.Resampling.LANCZOS
        )
    
    elif action == 'crop':
        return image.crop((
            params.get('crop_x', 0),
            params.get('crop_y', 0),
            params['width'],
            params['height']
        ))
    
    return image