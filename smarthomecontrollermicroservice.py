# Import necessary modules
import http
from flask import Flask, request, jsonify
import requests
import logging
import os

# Define the URL for Get Home Parameter Microservice using environment variable
homeurl = "http://54.163.126.180:5001/get-parameters"

# Define the URL for Risk Predictor Microservice using environment variable
home2url = "http://54.163.126.180:5002/predict-risk"

app = Flask(__name__)

# Assuming initial thermostat temperature
current_temperature = 20

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/adjust-thermostat', methods=['POST'])
def adjust_thermostat():
    # Receive voice command from the user
    try:
        voice_command = request.json.get('voice_command')  # Use .get() to avoid KeyError
    except KeyError:
        logging.error('Error: Missing "voice_command" in the request JSON data.')
        return jsonify({'error': 'Missing "voice_command" in the request JSON data'}), 400

    # Log the received voice command
    logging.info('Received voice command: %s', voice_command)

    # Communicate with Get Home Parameter Microservice
    try:
        home_parameters = requests.get(homeurl).json()
    except requests.exceptions.RequestException as e:
        # Log an error if there's an issue with the request
        logging.error('Error communicating with Get Home Parameter Microservice: %s', str(e))
        return jsonify({'error': 'Communication error with Get Home Parameter Microservice'}), 500

    # Log the retrieved home parameters
    logging.debug('Received home parameters: %s', home_parameters)

    # Communicate with Risk Predictor Microservice
    try:
        response = requests.post(home2url, json={'parameters': home_parameters})
        response_json = response.json()
    except requests.exceptions.RequestException as e:
        # Log an error if there's an issue with the request
        logging.error('Error communicating with Risk Predictor Microservice: %s', str(e))
        return jsonify({'error': 'Communication error with Risk Predictor Microservice'}), 500
    except ValueError as e:
        # Log an error if there's an issue parsing the response as JSON
        logging.error('Error parsing response from Risk Predictor Microservice as JSON: %s', str(e))
        logging.error('Response content: %s', response.content)
        return jsonify({'error': 'Error parsing response from Risk Predictor Microservice as JSON'}), 500

    # Log the predicted risk level
    logging.debug('Predicted risk level: %s', response_json)

    # Make a decision based on risk level and adjust thermostat if necessary
    if response_json.get('risk_level') == 'low':
        global current_temperature

        # Corrected URL for Home Automation Service
        home_automation_url = 'http://54.163.126.180:5000/update-temperature'

        # Communicate with Home Automation Service to adjust thermostat
        try:
            new_temperature = requests.post(home_automation_url, json={'temperature': current_temperature + 2}).json()
        except requests.exceptions.RequestException as e:
            # Log an error if there's an issue with the request
            logging.error('Error communicating with Home Automation Service: %s', str(e))
            return jsonify({'error': 'Communication error with Home Automation Service'}), 500

        # Log the adjusted thermostat temperature
        logging.info('Thermostat adjusted successfully. New temperature: %s°C', new_temperature)

        # Update the current temperature
        current_temperature = new_temperature  # Assuming new_temperature is just a single value

        return jsonify({'message': 'Thermostat adjusted successfully.', 'current_temperature': current_temperature})

    # Log if the adjustment is canceled
    logging.warning('Adjustment canceled due to high risk.')
    return jsonify({'message': 'Adjustment canceled due to high risk.'})

@app.route('/update-temperature', methods=['POST'])
def update_temperature():
    # Update thermostat temperature based on the request from Risk Predictor Microservice
    new_temperature = request.json['temperature']

    # Log the updated thermostat temperature
    logging.info('Received request to update thermostat temperature. New temperature: %s°C', new_temperature)

    global current_temperature
    current_temperature = new_temperature
    return jsonify({'temperature': current_temperature})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
