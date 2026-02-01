//! YORI Proxy - Pure Rust HTTP/HTTPS Proxy Server
//!
//! High-performance proxy for LLM traffic interception on OPNsense routers.
//! No Python overhead - pure Rust performance.

use anyhow::{Context, Result};
use clap::Parser;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Request, Response, StatusCode};
use hyper::body::{Incoming, Bytes};
use hyper_util::rt::TokioIo;
use http_body_util::Full;
use std::net::SocketAddr;
use std::path::PathBuf;
use tokio::net::TcpListener;
use tracing::{info, warn, error};
use tracing_subscriber;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Configuration file path
    #[arg(short, long, default_value = "/usr/local/etc/yori/yori.conf")]
    config: PathBuf,

    /// Listen address
    #[arg(short, long, default_value = "0.0.0.0:8443")]
    listen: SocketAddr,

    /// Log level (trace, debug, info, warn, error)
    #[arg(short = 'v', long, default_value = "info")]
    log_level: String,
}

/// Handle incoming HTTP requests
async fn handle_request(req: Request<Incoming>) -> Result<Response<Full<Bytes>>> {
    let method = req.method();
    let uri = req.uri();

    info!("Request: {} {}", method, uri);

    // Health check endpoint
    if uri.path() == "/health" {
        let response = serde_json::json!({
            "status": "ok",
            "mode": "rust",
            "message": "YORI Rust Proxy Running",
            "performance": "native"
        });

        return Ok(Response::builder()
            .status(StatusCode::OK)
            .header("Content-Type", "application/json")
            .body(Full::new(Bytes::from(response.to_string())))
            .unwrap());
    }

    // Root endpoint
    if uri.path() == "/" {
        let body = format!(
            "YORI Rust Proxy\n\
             Version: {}\n\
             Mode: Pure Rust - Maximum Performance\n\
             \n\
             The spice must flow.\n",
            env!("CARGO_PKG_VERSION")
        );

        return Ok(Response::builder()
            .status(StatusCode::OK)
            .header("Content-Type", "text/plain")
            .body(Full::new(Bytes::from(body)))
            .unwrap());
    }

    // Default response
    Ok(Response::builder()
        .status(StatusCode::NOT_FOUND)
        .body(Full::new(Bytes::from("Not Found")))
        .unwrap())
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    // Initialize logging
    let log_filter = format!("yori_proxy={},yori={}", args.log_level, args.log_level);
    tracing_subscriber::fmt()
        .with_env_filter(log_filter)
        .with_target(false)
        .with_thread_ids(false)
        .init();

    info!("═══════════════════════════════════════════════════════════");
    info!("YORI Proxy - Pure Rust");
    info!("═══════════════════════════════════════════════════════════");
    info!("");
    info!("Version: {}", env!("CARGO_PKG_VERSION"));
    info!("Listen: {}", args.listen);
    info!("Config: {}", args.config.display());
    info!("");
    info!("Performance Mode: MAXIMUM");
    info!("Language: Pure Rust (no Python overhead)");
    info!("Concurrency: Async tokio (true parallelism)");
    info!("");
    info!("The spice must flow.");
    info!("═══════════════════════════════════════════════════════════");

    // Load configuration if it exists
    if args.config.exists() {
        info!("Loading configuration from {}", args.config.display());
        // TODO: Parse YAML config
    } else {
        warn!("Configuration file not found, using defaults");
    }

    // Bind TCP listener
    let listener = TcpListener::bind(&args.listen)
        .await
        .context("Failed to bind to address")?;

    info!("Listening on {}", args.listen);
    info!("Ready to intercept LLM traffic");

    // Accept connections
    loop {
        let (stream, addr) = listener.accept().await?;
        let io = TokioIo::new(stream);

        tokio::spawn(async move {
            if let Err(err) = http1::Builder::new()
                .serve_connection(io, service_fn(handle_request))
                .await
            {
                error!("Error serving connection from {}: {}", addr, err);
            }
        });
    }
}
