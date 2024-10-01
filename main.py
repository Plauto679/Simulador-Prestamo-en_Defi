from flask import Flask, render_template, request, session, redirect, url_for, send_file
import random
import os
import matplotlib.pyplot as plt
import io

app = Flask(__name__)

# Set the secret key for session management
app.secret_key = os.urandom(24)

# Leaderboard will store a list of tuples (nickname, XOC balance)
leaderboard = []

# Initial game state
STARTING_ETH_COLLATERAL = 2  # 2 ETH at the start
STARTING_ETH_COLLATERAL_EXPRESSED_AS_XOC = round(STARTING_ETH_COLLATERAL * 25000, 2)  # ETH Collateral expressed in XOC
STARTING_LOAN = 30000  # Loan is 30,000 XOC
STARTING_XOC_BALANCE_IN_WALLET = 25000  # User starts with 25,000 XOC in their wallet

# Game ending logic and initial price
INITIAL_ETH_PRICE = 25000  # 1 ETH = 25,000 XOC initially
MAX_ROUNDS = 10  # Game ends at round 10
LIQUIDATION_THRESHOLD = 0.99  # Health ratio below 0.99 results in liquidation

# Initial ETH wallet balance (expressed in ETH and XOC)
STARTING_ETH_WALLET_BALANCE = 1  # User starts with 1 ETH in their wallet
STARTING_ETH_WALLET_BALANCE_EXPRESSED_AS_XOC = round(STARTING_ETH_WALLET_BALANCE * INITIAL_ETH_PRICE, 2)  # ETH in wallet expressed in XOC

def simulate_eth_price():
    """Simulates a random fluctuation in ETH price (-10% to +10%) and truncates to 2 decimals."""
    return round(INITIAL_ETH_PRICE * (1 + random.uniform(-0.1, 0.1)), 2)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    # Store the nickname in the session
    session['nickname'] = request.form['nickname']
    return redirect(url_for('game'))

@app.route('/game', methods=['GET', 'POST'])
def game():
    if 'round' not in session:
        session['round'] = 1
        session['eth_collateral'] = STARTING_ETH_COLLATERAL
        session['loan'] = STARTING_LOAN
        session['xoc_balance_in_wallet'] = STARTING_XOC_BALANCE_IN_WALLET
        session['eth_price'] = INITIAL_ETH_PRICE
        session['health_history'] = []
        session['eth_wallet_balance'] = STARTING_ETH_WALLET_BALANCE

        # Add initial health ratio to health history
        initial_health_ratio = round(session['eth_collateral'] * session['eth_price'] / session['loan'], 2)
        session['health_history'].append(initial_health_ratio)

    eth_collateral_in_xoc = round(session['eth_collateral'] * session['eth_price'], 2)
    health_ratio = round(eth_collateral_in_xoc / session['loan'], 2) if session['loan'] > 0 else 0
    eth_wallet_balance_expressed_as_xoc = round(session['eth_wallet_balance'] * session['eth_price'], 2)

    if health_ratio < LIQUIDATION_THRESHOLD:
        nickname = session.get('nickname', 'Unknown')
        final_balance = session.get('xoc_balance_in_wallet', 0)
        leaderboard.append((nickname, final_balance))
        return render_template('liquidation.html', final_health_ratio=health_ratio, leaderboard=leaderboard)

    if session['round'] > MAX_ROUNDS:
        nickname = session.get('nickname', 'Unknown')
        final_balance = session.get('xoc_balance_in_wallet', 0)
        leaderboard.append((nickname, final_balance))
        return render_template('end.html', 
                               final_eth_collateral=session['eth_collateral'], 
                               final_loan=session['loan'], 
                               final_balance=final_balance,
                               final_eth_price=session['eth_price'],
                               leaderboard=leaderboard)

    if request.method == 'POST':
        try:
            increase_collateral = round(float(request.form.get('increase_collateral', 0)), 2)
            decrease_collateral = round(float(request.form.get('decrease_collateral', 0)), 2)
            ask_loan = round(float(request.form.get('ask_loan', 0)), 2)
            repay_loan = round(float(request.form.get('repay_loan', 0)), 2)
        except ValueError:
            return redirect(url_for('game'))

        if increase_collateral > session['eth_wallet_balance']:
            error_message = f"You cannot increase collateral by {increase_collateral} as it exceeds your ETH Wallet balance of {session['eth_wallet_balance']}."
            return render_template('game.html', 
                                   round=session['round'], 
                                   eth_collateral=round(session['eth_collateral'], 2), 
                                   loan=round(session['loan'], 2), 
                                   xoc_balance_in_wallet=round(session['xoc_balance_in_wallet'], 2), 
                                   health_ratio=health_ratio,
                                   eth_price=round(session['eth_price'], 2),
                                   eth_collateral_in_xoc=eth_collateral_in_xoc,
                                   eth_wallet_balance=round(session['eth_wallet_balance'], 2),
                                   eth_wallet_balance_expressed_as_xoc=eth_wallet_balance_expressed_as_xoc,
                                   error_message=error_message)

        # Apply user actions to the session data

        # Update ETH collateral and ETH wallet balance when increasing collateral
        session['eth_collateral'] += increase_collateral
        session['eth_wallet_balance'] -= increase_collateral

        # Update ETH collateral and ETH wallet balance when decreasing collateral
        session['eth_collateral'] -= decrease_collateral
        session['eth_wallet_balance'] += decrease_collateral

        # Update Loan and XOC Balance when asking for more loan
        session['loan'] += ask_loan
        session['xoc_balance_in_wallet'] += ask_loan

        # Update Loan and XOC Balance when repaying the loan
        session['loan'] -= repay_loan
        session['xoc_balance_in_wallet'] -= repay_loan

        # Simulate ETH price fluctuation each round
        session['eth_price'] = simulate_eth_price()

        # XOC Balance increases by 5% each round
        session['xoc_balance_in_wallet'] = round(session['xoc_balance_in_wallet'] * 1.05, 2)

        # Recalculate ETH Balance Expressed in XOC (in Wallet)
        eth_wallet_balance_expressed_as_xoc = round(session['eth_wallet_balance'] * session['eth_price'], 2)

        # Store health ratio in history
        session['health_history'].append(health_ratio)

        # Move to the next round
        session['round'] += 1

        # Redirect to update the screen with the new game state
        return redirect(url_for('game'))

    return render_template('game.html', 
                           round=session['round'], 
                           eth_collateral=round(session['eth_collateral'], 2), 
                           loan=round(session['loan'], 2), 
                           xoc_balance_in_wallet=round(session['xoc_balance_in_wallet'], 2), 
                           health_ratio=health_ratio,
                           eth_price=round(session['eth_price'], 2),
                           eth_collateral_in_xoc=eth_collateral_in_xoc,
                           eth_wallet_balance=round(session['eth_wallet_balance'], 2),
                           eth_wallet_balance_expressed_as_xoc=eth_wallet_balance_expressed_as_xoc)

@app.route('/health_chart')
def health_chart():
    """Generate and serve the health ratio chart."""
    rounds = list(range(1, len(session['health_history']) + 1))
    health_factors = session['health_history']

    # Create the chart using Matplotlib
    plt.figure(figsize=(6, 4))
    plt.plot(rounds, health_factors, marker='o', color='green', label='Health Factor')

    # Label the last point with the current health ratio
    if health_factors:
        current_health_ratio = health_factors[-1]
        plt.annotate(f'Current: {current_health_ratio:.2f}', 
                     xy=(rounds[-1], health_factors[-1]), 
                     xytext=(rounds[-1], health_factors[-1] + 0.05),
                     arrowprops=dict(facecolor='black', arrowstyle="->"))

    plt.xlabel('Round')
    plt.ylabel('Health Factor')
    plt.title('Health Factor Over Rounds')
    plt.grid(True)
    plt.legend()

    # Save the figure to a BytesIO object and send it as a response
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return send_file(img, mimetype='image/png')

@app.route('/restart')
def restart_game():
    """Restart the game by clearing the session and redirecting to the home page."""
    session.clear()  # Clear all session data
    return redirect(url_for('home'))  # Redirect to the home page

if __name__ == '__main__':
    app.run(debug=True)
