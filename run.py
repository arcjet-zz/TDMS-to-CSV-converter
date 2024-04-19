from waitress import serve
from tdms6 import app 

serve(app, host='0.0.0.0', port=12333)