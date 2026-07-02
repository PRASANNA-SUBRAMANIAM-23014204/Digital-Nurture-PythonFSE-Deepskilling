"""
API Gateway - Routes requests to appropriate microservices

Responsibilities:
1. Route /api/courses/* → Course Service (port 5001)
2. Route /api/students/* → Student Service (port 5002)
3. Route /api/auth/* → Auth Service (port 5003)
4. Handle authentication header forwarding
5. Rate limiting (concept)
6. Request logging
"""

from flask import Flask, request, Response
import requests
import json
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Service URLs
COURSE_SERVICE_URL = "http://localhost:5001"
STUDENT_SERVICE_URL = "http://localhost:5002"
AUTH_SERVICE_URL = "http://localhost:5003"


def route_request(service_url, path, method, headers, data=None, params=None):
    """
    Route request to the appropriate microservice
    
    Args:
        service_url: Base URL of the target service
        path: Request path
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: Request headers (will forward auth headers)
        data: Request body data
        params: Query parameters
    
    Returns:
        Response from the microservice
    """
    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path
    
    target_url = f"{service_url}{path}"
    
    # Forward headers (remove host, keep authorization)
    forward_headers = {}
    
    # Copy relevant headers
    for key, value in headers.items():
        if key.lower() in ['content-type', 'authorization', 'accept']:
            forward_headers[key] = value
    
    # Ensure content-type is set if we have data
    if data and 'Content-Type' not in forward_headers:
        forward_headers['Content-Type'] = 'application/json'
    
    try:
        logging.info(f"Routing {method} {target_url}")
        
        # Make request to target service
        response = requests.request(
            method=method,
            url=target_url,
            headers=forward_headers,
            json=data if data else None,
            params=params if params else None,
            timeout=10  # 10 second timeout
        )
        
        # Return response from service
        return Response(
            response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )
    
    except requests.exceptions.ConnectionError:
        # Service unavailable
        return Response(
            json.dumps({
                'error': {
                    'code': 'SERVICE_UNAVAILABLE',
                    'message': 'Service is temporarily unavailable'
                }
            }),
            status=503,
            mimetype='application/json'
        )
    
    except requests.exceptions.Timeout:
        # Service timeout
        return Response(
            json.dumps({
                'error': {
                    'code': 'SERVICE_TIMEOUT',
                    'message': 'Service request timed out'
                }
            }),
            status=504,
            mimetype='application/json'
        )
    
    except Exception as e:
        # General error
        logging.error(f"Error routing request: {str(e)}")
        return Response(
            json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'An internal error occurred'
                }
            }),
            status=500,
            mimetype='application/json'
        )


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def gateway(path):
    """
    Main gateway route - routes all requests to appropriate services
    """
    # Get request details
    method = request.method
    headers = dict(request.headers)
    data = request.get_json() if request.is_json else None
    params = dict(request.args)
    
    # Construct full path with leading slash
    if not path.startswith('/') and path:
        path = '/' + path
    elif not path:
        path = '/'
    
    logging.info(f"Gateway received: {method} {path}")
    
    # Route based on path prefix
    if path.startswith('/api/courses') or path.startswith('/api/departments'):
        # Route to Course Service
        remaining_path = path.replace('/api/courses', '').replace('/api/departments', '')
        if not remaining_path or remaining_path == '/':
            remaining_path = '/' + path.split('/api/')[1] if '/api/' in path else path
        return route_request(COURSE_SERVICE_URL, path, method, headers, data, params)
    
    elif path.startswith('/api/students'):
        # Route to Student Service
        return route_request(STUDENT_SERVICE_URL, path, method, headers, data, params)
    
    elif path.startswith('/api/auth'):
        # Route to Auth Service
        return route_request(AUTH_SERVICE_URL, path, method, headers, data, params)
    
    elif path == '/health':
        # Gateway health check
        return health()
    
    else:
        # No matching service found
        return Response(
            json.dumps({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': f'No service found for path: {path}'
                }
            }),
            status=404,
            mimetype='application/json'
        )


@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint for the API Gateway
    """
    # Check if all services are healthy
    services_status = {}
    
    for service_name, service_url in [
        ('course_service', COURSE_SERVICE_URL),
        ('student_service', STUDENT_SERVICE_URL),
        ('auth_service', AUTH_SERVICE_URL)
    ]:
        try:
            response = requests.get(f"{service_url}/health", timeout=2)
            services_status[service_name] = 'healthy' if response.status_code == 200 else 'unhealthy'
        except:
            services_status[service_name] = 'unavailable'
    
    all_healthy = all(status == 'healthy' for status in services_status.values())
    
    return {
        'status': 'healthy' if all_healthy else 'degraded',
        'services': services_status
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)