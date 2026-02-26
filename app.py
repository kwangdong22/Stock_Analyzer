import sqlite3
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
import yfinance as yf

app = Flask(__name__)

# --- SYSTEM ARCHITECTURE: CACHING & DATABASE ---
# In-memory cache to prevent API rate-limiting and improve load speeds
API_CACHE = {}
CACHE_TTL = 300  # 5 minutes

def init_db():
    """Initializes the SQLite database for user state (Watchlist)"""
    conn = sqlite3.connect('market.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            added_on DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# --- FRONTEND TEMPLATE (HTML/JS/CSS) ---
# Embedded to create a seamless Single-Page Application (SPA)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Watcher</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-slate-50 text-slate-800 font-sans min-h-screen p-8">
    <div class="max-w-4xl mx-auto space-y-6">
        
        <!-- Header & Search -->
        <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex justify-between items-center">
            <h1 class="text-2xl font-bold text-slate-800">📈 Market Watcher Pro</h1>
            <form id="searchForm" class="flex gap-2">
                <input type="text" id="tickerInput" placeholder="Enter Ticker (e.g. AAPL)" class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 uppercase" required>
                <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-semibold transition-colors disabled:opacity-50" id="searchBtn">
                    Analyze
                </button>
            </form>
        </div>

        <!-- Error Banner -->
        <div id="errorBanner" class="hidden bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative"></div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Main Data & Chart -->
            <div class="md:col-span-2 space-y-6">
                <!-- Price Card -->
                <div id="priceCard" class="hidden bg-white p-6 rounded-xl shadow-sm border border-slate-100">
                    <div class="flex justify-between items-start">
                        <div>
                            <h2 id="stockSymbol" class="text-3xl font-bold text-slate-800">--</h2>
                            <p class="text-slate-500 text-sm">Real-time Quote</p>
                        </div>
                        <div class="text-right">
                            <div id="currentPrice" class="text-4xl font-bold">$--</div>
                            <div id="priceChange" class="text-lg font-semibold mt-1">--</div>
                        </div>
                    </div>
                </div>

                <!-- Chart Card -->
                <div id="chartCard" class="hidden bg-white p-6 rounded-xl shadow-sm border border-slate-100">
                    <h3 class="text-lg font-semibold mb-4 text-slate-700">30-Day Price History</h3>
                    <canvas id="stockChart" height="250"></canvas>
                </div>
            </div>

            <!-- Watchlist Sidebar -->
            <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-100 h-fit">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold text-slate-700">My Watchlist</h3>
                    <button onclick="addToWatchlist()" id="addWatchlistBtn" class="hidden text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1 rounded transition-colors">+ Add Current</button>
                </div>
                <ul id="watchlistContainer" class="space-y-2">
                    <li class="text-slate-400 text-sm italic">Loading watchlist...</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        let priceChart = null;
        let currentTicker = '';

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadWatchlist();
        });

        // Handle Form Submit (AJAX Request)
        document.getElementById('searchForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const ticker = document.getElementById('tickerInput').value.toUpperCase();
            fetchStockData(ticker);
        });

        async function fetchStockData(ticker) {
            const btn = document.getElementById('searchBtn');
            const errorBanner = document.getElementById('errorBanner');
            
            btn.disabled = true;
            btn.innerText = 'Loading...';
            errorBanner.classList.add('hidden');

            try {
                // Fetch from our RESTful Backend
                const response = await fetch(`/api/quote/${ticker}`);
                const data = await response.json();

                if (!response.ok) throw new Error(data.error || 'Failed to fetch data');

                currentTicker = ticker;
                updateUI(data);
            } catch (error) {
                errorBanner.innerText = error.message;
                errorBanner.classList.remove('hidden');
            } finally {
                btn.disabled = false;
                btn.innerText = 'Analyze';
            }
        }

        function updateUI(data) {
            // Update Price Card
            document.getElementById('priceCard').classList.remove('hidden');
            document.getElementById('chartCard').classList.remove('hidden');
            document.getElementById('addWatchlistBtn').classList.remove('hidden');
            
            document.getElementById('stockSymbol').innerText = data.symbol;
            document.getElementById('currentPrice').innerText = `$${data.price.toFixed(2)}`;
            
            const changeEl = document.getElementById('priceChange');
            const isPositive = data.change >= 0;
            changeEl.innerText = `${isPositive ? '+' : ''}${data.change.toFixed(2)}%`;
            changeEl.className = `text-lg font-semibold mt-1 ${isPositive ? 'text-green-600' : 'text-red-600'}`;

            // Update Chart
            if (priceChart) priceChart.destroy();
            const ctx = document.getElementById('stockChart').getContext('2d');
            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.history.dates,
                    datasets: [{
                        label: 'Closing Price ($)',
                        data: data.history.prices,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    interaction: { intersect: false, mode: 'index' },
                    plugins: { legend: { display: false } },
                    scales: { x: { display: false } }
                }
            });
        }

        async function loadWatchlist() {
            const res = await fetch('/api/watchlist');
            const items = await res.json();
            const container = document.getElementById('watchlistContainer');
            
            if (items.length === 0) {
                container.innerHTML = '<li class="text-slate-400 text-sm italic">Watchlist is empty.</li>';
                return;
            }

            container.innerHTML = items.map(item => `
                <li class="flex justify-between items-center p-3 bg-slate-50 rounded border border-slate-100 hover:bg-slate-100 cursor-pointer transition-colors" onclick="fetchStockData('${item.ticker}')">
                    <span class="font-semibold">${item.ticker}</span>
                    <button onclick="event.stopPropagation(); removeFromWatchlist('${item.ticker}')" class="text-red-400 hover:text-red-600 text-sm">✖</button>
                </li>
            `).join('');
        }

        async function addToWatchlist() {
            if (!currentTicker) return;
            await fetch('/api/watchlist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker: currentTicker })
            });
            loadWatchlist();
        }

        async function removeFromWatchlist(ticker) {
            await fetch(`/api/watchlist/${ticker}`, { method: 'DELETE' });
            loadWatchlist();
        }
    </script>
</body>
</html>
"""

# --- BACKEND RESTful API ROUTES ---

@app.route('/')
def home():
    """Serves the Single Page Application"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/quote/<ticker>', methods=['GET'])
def get_quote(ticker):
    """API Endpoint: Fetches stock data with Caching to optimize performance"""
    ticker = ticker.upper()
    current_time = time.time()

    # 1. Check Cache
    if ticker in API_CACHE:
        cache_entry = API_CACHE[ticker]
        if current_time - cache_entry['timestamp'] < CACHE_TTL:
            return jsonify(cache_entry['data'])

    # 2. Fetch fresh data if not in cache or expired
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        
        if len(hist) < 2:
            return jsonify({"error": "Ticker not found or insufficient data"}), 404

        current_price = float(hist['Close'].iloc[-1])
        prev_price = float(hist['Close'].iloc[-2])
        change_percent = ((current_price - prev_price) / prev_price) * 100

        # Package data for frontend
        data = {
            "symbol": ticker,
            "price": current_price,
            "change": change_percent,
            "history": {
                "dates": hist.index.strftime('%Y-%m-%d').tolist(),
                "prices": hist['Close'].tolist()
            }
        }

        # 3. Save to Cache
        API_CACHE[ticker] = {
            'timestamp': current_time,
            'data': data
        }

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/watchlist', methods=['GET', 'POST'])
def manage_watchlist():
    """API Endpoint: Handles Database CRUD operations for the Watchlist"""
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT ticker FROM watchlist ORDER BY added_on DESC")
        items = [{"ticker": row[0]} for row in cursor.fetchall()]
        conn.close()
        return jsonify(items)

    if request.method == 'POST':
        ticker = request.json.get('ticker').upper()
        try:
            cursor.execute("INSERT INTO watchlist (ticker) VALUES (?)", (ticker,))
            conn.commit()
        except sqlite3.IntegrityError:
            pass # Ignore duplicates
        finally:
            conn.close()
        return jsonify({"status": "success", "ticker": ticker})

@app.route('/api/watchlist/<ticker>', methods=['DELETE'])
def delete_from_watchlist(ticker):
    """API Endpoint: Removes item from database"""
    conn = sqlite3.connect('market.db')
    conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

if __name__ == '__main__':
    init_db()  # Initialize database on startup
    app.run(debug=True)