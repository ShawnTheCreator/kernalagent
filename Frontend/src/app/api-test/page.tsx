"use client";

import { useEffect, useState } from "react";

/**
 * API Test Component
 * 
 * Tests Vercel environment variable injection and backend connectivity.
 * This is a throwaway test component - delete after verification.
 * 
 * SUCCESS: Shows "Skills loaded: X" with green background
 * FAILURE: Shows error message with red background
 */
export default function ApiTestPage() {
    const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
    const [message, setMessage] = useState("");
    const [skillCount, setSkillCount] = useState(0);
    const [rawResponse, setRawResponse] = useState("");

    // Get the API base URL from environment
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "NOT SET";

    useEffect(() => {
        // Log to console for debugging
        console.log("=== API TEST ===");
        console.log("NEXT_PUBLIC_API_BASE_URL:", apiBaseUrl);

        // Skip fetch if env var not set
        if (apiBaseUrl === "NOT SET") {
            setStatus("error");
            setMessage("Environment variable NEXT_PUBLIC_API_BASE_URL is NOT SET");
            return;
        }

        // Test the /skills endpoint
        const testBackend = async () => {
            const url = `${apiBaseUrl}/skills`;
            console.log("Fetching:", url);

            try {
                const response = await fetch(url, {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                    },
                });

                console.log("Response status:", response.status);

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error("Non-200 response:", errorText);
                    setStatus("error");
                    setMessage(`HTTP ${response.status}: ${errorText}`);
                    setRawResponse(errorText);
                    return;
                }

                const data = await response.json();
                console.log("Response data:", data);

                // Handle both array and object responses
                const skills = Array.isArray(data) ? data : data.skills || [];

                setStatus("success");
                setSkillCount(skills.length);
                setMessage(`Skills loaded: ${skills.length}`);
                setRawResponse(JSON.stringify(data, null, 2));

            } catch (err: any) {
                console.error("Fetch error:", err);
                setStatus("error");

                // Provide helpful error messages
                if (err.message.includes("Failed to fetch")) {
                    setMessage("Network error - CORS issue or backend unreachable");
                } else {
                    setMessage(err.message || "Unknown error");
                }
                setRawResponse(String(err));
            }
        };

        testBackend();
    }, [apiBaseUrl]);

    return (
        <div style={{ padding: "20px", fontFamily: "monospace" }}>
            <h1>🧪 API Connectivity Test</h1>

            {/* Environment Variable */}
            <div style={{
                marginBottom: "20px",
                padding: "10px",
                background: "#f0f0f0",
                borderRadius: "5px"
            }}>
                <strong>NEXT_PUBLIC_API_BASE_URL:</strong>
                <br />
                <code style={{ color: apiBaseUrl === "NOT SET" ? "red" : "green" }}>
                    {apiBaseUrl}
                </code>
            </div>

            {/* Status */}
            <div style={{
                padding: "15px",
                borderRadius: "5px",
                marginBottom: "20px",
                background: status === "loading" ? "#fff3cd" :
                    status === "success" ? "#d4edda" : "#f8d7da",
                color: status === "loading" ? "#856404" :
                    status === "success" ? "#155724" : "#721c24"
            }}>
                <strong>Status: </strong>
                {status === "loading" && "⏳ Testing..."}
                {status === "success" && `✅ ${message}`}
                {status === "error" && `❌ ${message}`}
            </div>

            {/* Raw Response (for debugging) */}
            {rawResponse && (
                <div>
                    <strong>Raw Response:</strong>
                    <pre style={{
                        background: "#1e1e1e",
                        color: "#d4d4d4",
                        padding: "10px",
                        borderRadius: "5px",
                        overflow: "auto",
                        maxHeight: "300px",
                        fontSize: "12px"
                    }}>
                        {rawResponse}
                    </pre>
                </div>
            )}

            {/* Instructions */}
            <div style={{ marginTop: "20px", fontSize: "12px", color: "#666" }}>
                <p><strong>How to read results:</strong></p>
                <ul>
                    <li>🟢 Green = Backend reachable, skills loaded</li>
                    <li>🔴 Red = Error (check message for details)</li>
                    <li>🟡 Yellow = Still loading</li>
                </ul>
                <p>Check browser console (F12) for detailed logs.</p>
            </div>
        </div>
    );
}
