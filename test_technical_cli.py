"""CLI Technical Analysis Verification Script for Gold AI Trading System.

Tests multi-timeframe indicator calculations (EMA, RSI, MACD, ATR, Support/Resistance, Trend)
and prints formatted reports with color-coded analysis.
"""
import sys
import os

# Force UTF-8 stdout if possible on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import get_settings
from src.models.market_data import Timeframe
from src.models.technical_analysis import TechnicalAnalysisResponse, TrendDirection, RSICondition, MACDState
from src.services.technical_service import get_technical_service

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
    title = "[*] GOLD (XAU/USD) TECHNICAL ANALYSIS ENGINE - PHASE 2"
    if RICH_AVAILABLE and console:
        try:
            console.print(Panel(f"[bold yellow]{title}[/bold yellow]\n[cyan]Multi-Indicator Calculations & Multi-Confirmation Trend Detection[/cyan]", expand=False))
            return
        except Exception:
            pass
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def display_analysis(res: TechnicalAnalysisResponse):
    if RICH_AVAILABLE and console:
        try:
            # Trend styling
            if res.trend.direction == TrendDirection.BULLISH:
                trend_str = f"[bold green]BULLISH ({res.trend.strength}, {res.trend.score:+0.2f})[/bold green]"
            elif res.trend.direction == TrendDirection.BEARISH:
                trend_str = f"[bold red]BEARISH ({res.trend.strength}, {res.trend.score:+0.2f})[/bold red]"
            else:
                trend_str = f"[bold yellow]SIDEWAYS ({res.trend.strength}, {res.trend.score:+0.2f})[/bold yellow]"

            table = Table(
                title=f"[Technical Analysis - {res.timeframe.value.upper()}] (Price: ${res.current_price:,.2f})",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Indicator / Metric", style="bold cyan", width=24)
            table.add_column("Value / Details", style="bold white")

            table.add_row("Current Price", f"${res.current_price:,.2f} USD")
            ema20_str = f"EMA20: ${res.ema20:,.2f}" if res.ema20 else "EMA20: N/A"
            ema50_str = f"EMA50: ${res.ema50:,.2f}" if res.ema50 else "EMA50: N/A"
            ema200_str = f"EMA200: ${res.ema200:,.2f}" if res.ema200 else "EMA200: N/A (<200 bars)"
            table.add_row("Moving Averages", f"{ema20_str} | {ema50_str} | {ema200_str}")

            # RSI
            if res.rsi14 and res.rsi14.value is not None:
                rsi_color = "red" if res.rsi14.condition == RSICondition.OVERBOUGHT else ("green" if res.rsi14.condition == RSICondition.OVERSOLD else "white")
                rsi_str = f"[{rsi_color}]{res.rsi14.value:.2f} ({res.rsi14.condition.value})[/{rsi_color}]"
            else:
                rsi_str = "N/A"
            table.add_row("RSI (14)", rsi_str)

            # MACD
            if res.macd and res.macd.histogram is not None:
                macd_color = "green" if res.macd.state == MACDState.BULLISH else ("red" if res.macd.state == MACDState.BEARISH else "yellow")
                macd_str = (
                    f"Line: {res.macd.macd_line:+.2f} | Signal: {res.macd.signal_line:+.2f} | "
                    f"Hist: [{macd_color}]{res.macd.histogram:+.2f} ({res.macd.state.value})[/{macd_color}]"
                )
            else:
                macd_str = "N/A"
            table.add_row("MACD (12, 26, 9)", macd_str)

            # ATR
            if res.atr14 and res.atr14.value is not None:
                atr_str = f"${res.atr14.value:.2f} USD ({res.atr14.volatility_pct:.2f}% volatility)"
            else:
                atr_str = "N/A"
            table.add_row("ATR (14 Volatility)", atr_str)

            # Key Levels
            sup_str = ", ".join(f"${s:,.2f}" for s in res.support_levels) if res.support_levels else "None detected"
            res_str = ", ".join(f"${r:,.2f}" for r in res.resistance_levels) if res.resistance_levels else "None detected"
            table.add_row("Support Levels", f"[green]{sup_str}[/green]")
            table.add_row("Resistance Levels", f"[red]{res_str}[/red]")

            # Trend & Quality
            table.add_row("Market Trend", trend_str)
            table.add_row("Confirmations", " • " + "\n • ".join(res.trend.confirmations) if res.trend.confirmations else "None")
            table.add_row("Data Quality", f"{res.data_quality.notes}")

            console.print(table)
            return
        except Exception:
            pass

    print(f"\n--- Technical Analysis: {res.timeframe.value.upper()} ---")
    print(f"Price:        ${res.current_price:,.2f}")
    print(f"EMA 20/50/200:{res.ema20} / {res.ema50} / {res.ema200}")
    print(f"RSI 14:       {res.rsi14.value if res.rsi14 else 'N/A'}")
    print(f"MACD:         {res.macd}")
    print(f"ATR 14:       {res.atr14.value if res.atr14 else 'N/A'}")
    print(f"Supports:     {res.support_levels}")
    print(f"Resistances:  {res.resistance_levels}")
    print(f"Trend:        {res.trend.direction.value} ({res.trend.strength}, score: {res.trend.score})")
    print(f"Summary:      {res.indicator_summary}")


def main():
    print_header()
    service = get_technical_service()

    timeframes = [Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.D1]

    for tf in timeframes:
        print(f"\n🔍 Calculating Technical Analysis for [{tf.value.upper()}] Timeframe...")
        try:
            res = service.analyze(timeframe=tf)
            display_analysis(res)
        except Exception as exc:
            print(f"[!] Error analyzing timeframe {tf.value}: {exc}")

    print("\n[OK] Phase 2 Technical Analysis Engine Verification Completed!")


if __name__ == "__main__":
    main()
