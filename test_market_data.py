"""CLI Market Data Verification Script for Gold AI Trading System.

Tests live price retrieval and OHLCV candle feeds across multiple timeframes.
Prints cleanly formatted terminal tables and summary statistics.
"""
import sys
import os
from typing import List

# Force UTF-8 stdout if possible on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import get_settings
from src.models.market_data import Timeframe, PriceQuote, CandleHistory
from src.services.market_service import get_market_service

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console(highlight=False)
    RICH_AVAILABLE = True
except Exception:
    RICH_AVAILABLE = False
    console = None


def print_header():
    title = "[*] GOLD (XAU/USD) MARKET DATA VERIFICATION - PHASE 1"
    if RICH_AVAILABLE and console:
        try:
            console.print(Panel(f"[bold yellow]{title}[/bold yellow]\n[cyan]AI Trading Analysis Architecture[/cyan]", expand=False))
            return
        except Exception:
            pass
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def display_price(quote: PriceQuote):
    if RICH_AVAILABLE and console:
        try:
            table = Table(title="[XAU/USD Live Spot Price]", show_header=True, header_style="bold magenta")
            table.add_column("Property", style="bold cyan")
            table.add_column("Value", style="bold yellow")

            table.add_row("Symbol", quote.symbol)
            table.add_row("Spot Price", f"${quote.price:,.2f} {quote.currency}")
            table.add_row("Bid", f"${quote.bid:,.2f}" if quote.bid else "N/A")
            table.add_row("Ask", f"${quote.ask:,.2f}" if quote.ask else "N/A")
            table.add_row("Spread", f"${quote.spread:.4f}" if quote.spread is not None else "N/A")
            table.add_row("Unit", quote.unit)
            table.add_row("Provider", f"[green]{quote.provider}[/green]")
            table.add_row("Timestamp", quote.timestamp)
            table.add_row("Stale Flag", "Yes" if quote.is_stale else "No")
            console.print(table)
            return
        except Exception:
            pass

    print("\n--- Live XAU/USD Spot Price ---")
    print(f"Symbol:     {quote.symbol}")
    print(f"Price:      ${quote.price:,.2f} {quote.currency}")
    print(f"Bid / Ask:  ${quote.bid} / ${quote.ask} (Spread: ${quote.spread})")
    print(f"Provider:   {quote.provider}")
    print(f"Timestamp:  {quote.timestamp}")


def display_candles(history: CandleHistory):
    if not history.candles:
        print(f"No candles returned for {history.timeframe.value}")
        return

    if RICH_AVAILABLE and console:
        try:
            table = Table(
                title=f"[Historical OHLCV Candles - {history.timeframe.value.upper()}] ({history.count} bars via {history.provider})",
                show_header=True,
                header_style="bold blue",
            )
            table.add_column("Timestamp (UTC)", style="dim")
            table.add_column("Open ($)", justify="right")
            table.add_column("High ($)", justify="right", style="green")
            table.add_column("Low ($)", justify="right", style="red")
            table.add_column("Close ($)", justify="right", style="bold")
            table.add_column("Change", justify="right")
            table.add_column("Volume", justify="right", style="cyan")

            # Display last 8 candles
            display_list = history.candles[-8:]
            for c in display_list:
                change = c.close - c.open
                change_pct = (change / c.open) * 100 if c.open else 0.0
                color = "green" if change >= 0 else "red"
                chg_str = f"[{color}]{change:+.2f} ({change_pct:+.2f}%)[/{color}]"
                vol_str = f"{c.volume:,.0f}" if c.volume is not None else "-"

                table.add_row(
                    c.timestamp.replace("T", " ").replace("Z", "")[:19],
                    f"{c.open:,.2f}",
                    f"{c.high:,.2f}",
                    f"{c.low:,.2f}",
                    f"{c.close:,.2f}",
                    chg_str,
                    vol_str,
                )
            console.print(table)
            return
        except Exception:
            pass

    print(f"\n--- Candles: {history.timeframe.value} ({history.count} bars via {history.provider}) ---")
    print(f"{'Timestamp':<22} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Vol':<8}")
    for c in history.candles[-8:]:
        v = f"{c.volume:.0f}" if c.volume else "-"
        print(f"{c.timestamp[:19]:<22} {c.open:<10.2f} {c.high:<10.2f} {c.low:<10.2f} {c.close:<10.2f} {v:<8}")


def main():
    print_header()
    settings = get_settings()
    service = get_market_service()

    print(f"\n[Settings]")
    print(f"   - Environment:      {settings.APP_ENV}")
    print(f"   - Provider Mode:    {settings.MARKET_DATA_PROVIDER}")
    print(f"   - Base Symbol:      {settings.DEFAULT_SYMBOL}")
    print(f"   - Gold API Key Set: {'Yes' if settings.GOLDPRICE_DEV_API_KEY else 'No (using public/free tier)'}")

    # 1. Test Live Spot Price
    print("\n[Step 1/3] Fetching Live XAU/USD Spot Price...")
    try:
        quote = service.get_live_price()
        display_price(quote)
    except Exception as exc:
        print(f"[!] Error fetching live price: {exc}")

    # 2. Test Multiple Timeframes (1m, 5m, 15m, 1h, 1d)
    print("\n[Step 2/3] Fetching OHLCV Candlestick Feeds for Timeframes (1m, 5m, 15m, 1h, 1d)...")
    test_timeframes = [
        Timeframe.M1,
        Timeframe.M5,
        Timeframe.M15,
        Timeframe.H1,
        Timeframe.D1,
    ]

    for tf in test_timeframes:
        try:
            history = service.get_candles(timeframe=tf, limit=15)
            display_candles(history)
        except Exception as exc:
            print(f"[!] Error fetching timeframe {tf.value}: {exc}")

    # 3. Test Market Status
    print("\n[Step 3/3] Checking Market Data Service Status...")
    status = service.get_market_status()
    if RICH_AVAILABLE and console:
        try:
            status_color = "green" if status.status == "healthy" else "yellow"
            console.print(Panel(
                f"Status: [{status_color}]{status.status.upper()}[/{status_color}]\n"
                f"Details: {status.message}\n"
                f"Intraday Supported: {'Yes' if status.intraday_supported else 'No'}\n"
                f"Checked At: {status.timestamp}",
                title="Market Feed Health Check",
            ))
        except Exception:
            print(f"Status: {status.status.upper()} | {status.message}")
    else:
        print(f"Status: {status.status.upper()} | {status.message}")

    print("\n[OK] Phase 1 Market Data Verification Completed Successfully!")


if __name__ == "__main__":
    main()
