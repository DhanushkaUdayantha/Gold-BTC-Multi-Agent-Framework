"""CLI AI Market Analysis Verification Script for Gold AI Trading System.

Gathers multi-timeframe indicators (5m, 15m, 1h, 1d), runs AI analysis,
and prints a formatted terminal report with executive market summary.
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
from src.models.ai_analysis import (
    AIAnalysisResponse,
    MarketCondition,
    OverallBias,
    RiskLevel,
)
from src.services.ai_service import get_ai_service

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
    title = "[*] GOLD (XAU/USD) AI MARKET ANALYSIS - PHASE 3"
    if RICH_AVAILABLE and console:
        try:
            console.print(Panel(f"[bold yellow]{title}[/bold yellow]\n[cyan]Multi-Timeframe AI Synthesis & Institutional Market Structure[/cyan]", expand=False))
            return
        except Exception:
            pass
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def display_ai_analysis(res: AIAnalysisResponse):
    if RICH_AVAILABLE and console:
        try:
            # Bias color
            if res.overall_bias == OverallBias.BULLISH:
                bias_str = f"[bold green]BULLISH ({res.confidence}% Confidence)[/bold green]"
            elif res.overall_bias == OverallBias.BEARISH:
                bias_str = f"[bold red]BEARISH ({res.confidence}% Confidence)[/bold red]"
            else:
                bias_str = f"[bold yellow]NEUTRAL / WAIT ({res.confidence}% Confidence)[/bold yellow]"

            # Risk color
            if res.risk_level == RiskLevel.LOW:
                risk_str = "[bold green]LOW[/bold green]"
            elif res.risk_level == RiskLevel.MEDIUM:
                risk_str = "[bold yellow]MEDIUM[/bold yellow]"
            else:
                risk_str = "[bold red]HIGH[/bold red]"

            table = Table(
                title=f"[AI Market Structure Assessment] ({res.symbol} @ {res.analysis_timestamp[:19]})",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Category", style="bold cyan", width=22)
            table.add_column("AI Synthesis / Findings", style="bold white")

            table.add_row("Market Condition", f"[bold yellow]{res.market_condition.value}[/bold yellow]")
            table.add_row("Overall Bias", bias_str)
            table.add_row("Risk Level", risk_str)
            table.add_row("AI Provider Used", f"[green]{res.provider_used}[/green]" + (" (Built-in Heuristic Engine)" if res.is_fallback else ""))

            # Timeframe breakdowns
            tf_lines = []
            for tf_key, tf_desc in res.timeframe_analysis.items():
                tf_lines.append(f" • [bold cyan]{tf_key.upper()}[/bold cyan]: {tf_desc}")
            table.add_row("Timeframe Analysis", "\n".join(tf_lines))

            # Bullish / Bearish factors
            bull_lines = [" • " + f for f in res.key_bullish_factors] if res.key_bullish_factors else ["None"]
            bear_lines = [" • " + f for f in res.key_bearish_factors] if res.key_bearish_factors else ["None"]
            table.add_row("Bullish Factors", f"[green]{chr(10).join(bull_lines)}[/green]")
            table.add_row("Bearish Factors", f"[red]{chr(10).join(bear_lines)}[/red]")

            # Support & Resistance
            sup_str = ", ".join(f"${s:,.2f}" for s in res.key_support) if res.key_support else "None detected"
            res_str = ", ".join(f"${r:,.2f}" for r in res.key_resistance) if res.key_resistance else "None detected"
            table.add_row("Key Supports", f"[green]{sup_str}[/green]")
            table.add_row("Key Resistances", f"[red]{res_str}[/red]")

            console.print(table)

            # Executive Summary Panel
            console.print(Panel(
                f"[bold white]{res.summary}[/bold white]",
                title="[bold yellow]Executive Market Summary[/bold yellow]",
                border_style="cyan",
            ))

            # Configuration guidance if fallback
            if res.config_warning:
                console.print(Panel(
                    f"[yellow]{res.config_warning}[/yellow]",
                    title="[bold yellow]Configuration Notice[/bold yellow]",
                    border_style="yellow",
                ))
            return
        except Exception:
            pass

    print(f"\n--- AI Market Analysis for {res.symbol} ---")
    print(f"Condition:    {res.market_condition.value}")
    print(f"Bias:         {res.overall_bias.value} ({res.confidence}% confidence)")
    print(f"Risk Level:   {res.risk_level.value}")
    print(f"Provider:     {res.provider_used}")
    print(f"Summary:      {res.summary}")
    if res.config_warning:
        print(f"Notice:       {res.config_warning}")


def main():
    print_header()
    settings = get_settings()
    service = get_ai_service()

    print(f"\n[AI Settings]")
    print(f"   - Configured Provider: {settings.AI_PROVIDER}")
    print(f"   - Target Model:        {settings.AI_MODEL}")
    print(f"   - Gemini API Key:      {'Configured' if settings.GEMINI_API_KEY else 'Not Set (using Fallback Engine)'}")
    print(f"   - OpenAI API Key:      {'Configured' if settings.OPENAI_API_KEY else 'Not Set'}")

    print("\n🔍 [1/2] Aggregating Multi-Timeframe Data (5m, 15m, 1h, 1d)...")
    try:
        raw = service.get_raw_technical_input()
        print(f"   [OK] Aggregated {raw.timeframe_count} timeframes. Alignment: {raw.alignment_summary}")
    except Exception as exc:
        print(f"   [!] Error collecting multi-timeframe data: {exc}")
        return

    print("\n🔍 [2/2] Generating AI Market Structure Analysis...")
    try:
        analysis = service.analyze_market()
        display_ai_analysis(analysis)
    except Exception as exc:
        print(f"   [!] Error executing AI analysis: {exc}")
        return

    print("\n[OK] Phase 3 AI Market Analysis Verification Completed Successfully!")


if __name__ == "__main__":
    main()
