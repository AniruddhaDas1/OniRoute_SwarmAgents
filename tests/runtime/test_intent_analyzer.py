"""Unit & Integration tests for Intent Analysis Engine (Phase P1.I1)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.intent import (
    EmptyRequestError,
    IntentAnalysisError,
    IntentAnalyzer,
    IntentReport,
)
from runtime.intent.taxonomy import SUPPORTED_PROJECT_TYPES

runner = CliRunner()


def test_intent_report_immutability():
    analyzer = IntentAnalyzer()
    report = analyzer.analyze("Build a CRM using Next.js")
    assert isinstance(report, IntentReport)

    with pytest.raises(Exception):  # Frozen Pydantic model raises ValidationError/FrozenInstanceError
        report.primary_intent = "refactor"  # type: ignore


def test_empty_request_raises_error():
    analyzer = IntentAnalyzer()
    with pytest.raises(EmptyRequestError):
        analyzer.analyze("")
    with pytest.raises(EmptyRequestError):
        analyzer.analyze("   \n\t  ")


def test_simple_request_analysis():
    analyzer = IntentAnalyzer()
    report = analyzer.analyze("Build CRM")
    assert report.primary_intent == "build"
    assert report.project_category == "CRM"
    assert report.application_type == "Web Application"
    assert report.confidence_score >= 0.80
    assert len(report.unknown_items) == 0


def test_complex_request_analysis():
    analyzer = IntentAnalyzer()
    prompt = "Build a luxury real estate website using Next.js and Supabase with Stripe payments"
    report = analyzer.analyze(prompt)

    assert report.primary_intent == "build"
    assert report.project_category == "Website"
    assert report.application_type == "Web Application"
    assert "Next.js" in report.detected_frameworks
    assert "React" in report.detected_frameworks  # Implied
    assert "Supabase" in report.detected_database
    assert "PostgreSQL" in report.detected_database  # Implied
    assert "Stripe" in report.detected_integrations
    assert "luxury_real_estate" in report.detected_features
    assert "payment_processing" in report.detected_features
    assert report.confidence_score >= 0.85


def test_multiple_technologies_and_implied_stack():
    analyzer = IntentAnalyzer()
    prompt = "Create Flutter ecommerce app using Firebase Auth, Tailwind, Docker and OpenAI"
    report = analyzer.analyze(prompt)

    assert report.primary_intent == "build"
    assert report.project_category in ("E-commerce", "Mobile App")
    assert "Flutter" in report.detected_frameworks
    assert "Dart" in report.detected_languages  # Implied by Flutter
    assert "Firebase Auth" in report.detected_authentication
    assert "Tailwind" in report.detected_technologies
    assert "Docker" in report.detected_cloud
    assert "OpenAI" in report.detected_integrations
    assert report.confidence_score >= 0.80


def test_ambiguous_request_confidence_scoring():
    analyzer = IntentAnalyzer()
    report = analyzer.analyze("do something vague")

    assert report.confidence_score < 0.80
    assert len(report.unknown_items) > 0
    assert "Project category could not be clearly identified" in report.unknown_items


def test_unknown_request_analysis():
    analyzer = IntentAnalyzer()
    report = analyzer.analyze("asdfghjkl zxcvbnm")

    assert report.project_category == "Unknown"
    assert report.application_type == "Unknown Application"
    assert report.confidence_score < 0.50
    assert len(report.unknown_items) > 0


def test_supported_project_types_coverage():
    analyzer = IntentAnalyzer()
    test_cases = [
        ("Build a landing page", "Landing Page"),
        ("Create an ERP system", "ERP"),
        ("Build admin dashboard", "Dashboard"),
        ("Personal portfolio website", "Portfolio"),
        ("Technical blog with CMS", "Blog"),
        ("Online store shop", "E-commerce"),
        ("Multi-vendor marketplace", "Marketplace"),
        ("Food ordering restaurant app", "Restaurant"),
        ("School LMS platform", "School"),
        ("Hospital clinic portal", "Hospital"),
        ("Mobile app for iOS and Android", "Mobile App"),
        ("Desktop application with Electron", "Desktop App"),
        ("CLI tool for log parsing", "CLI Tool"),
        ("REST API service", "API"),
        ("Software development kit SDK", "SDK"),
        ("Autonomous AI Agent system", "AI Agent"),
        ("Web scraper automation script", "Automation"),
        ("Chrome browser extension", "Browser Extension"),
        ("Indie 2D game", "Game"),
    ]
    for prompt, expected_category in test_cases:
        report = analyzer.analyze(prompt)
        assert report.project_category == expected_category, f"Failed for prompt: '{prompt}'"


def test_supported_stack_detection_coverage():
    analyzer = IntentAnalyzer()
    prompt = "React Next.js Vue Angular Flutter React Native Node.js Python FastAPI Django Laravel .NET Go Rust Java Spring Supabase Appwrite Firebase PostgreSQL MySQL MongoDB Redis Docker Kubernetes Tailwind Shadcn Stripe OpenAI Gemini Anthropic"
    report = analyzer.analyze(prompt)

    expected_items = [
        "React", "Next.js", "Vue", "Angular", "Flutter", "React Native", "Node.js",
        "Python", "FastAPI", "Django", "Laravel", ".NET", "Go", "Rust", "Java",
        "Spring", "Supabase", "Appwrite", "Firebase", "PostgreSQL", "MySQL",
        "MongoDB", "Redis", "Docker", "Kubernetes", "Tailwind", "Shadcn",
        "Stripe", "OpenAI", "Gemini", "Anthropic",
    ]
    for item in expected_items:
        assert item in report.detected_technologies, f"Expected {item} in detected technologies: {report.detected_technologies}"


def test_cli_intent_diagnostic_command():
    result = runner.invoke(app, ["intent", "Build luxury hotel website using Next.js"])
    assert result.exit_code == 0
    assert "Intent Report:" in result.output
    assert "Website" in result.output
    assert "Next.js" in result.output


def test_cli_intent_diagnostic_command_json():
    result = runner.invoke(app, ["intent", "Build luxury hotel website using Next.js", "--json"])
    assert result.exit_code == 0
    assert '"project_category": "Website"' in result.output
    assert '"Next.js"' in result.output
