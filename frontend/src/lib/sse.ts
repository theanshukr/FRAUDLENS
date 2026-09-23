/* eslint-disable @typescript-eslint/no-explicit-any */
export type SSEEvent = {
  type: string;
  [key: string]: any;
};

export class InvestigationStream {
  private eventSource: EventSource | null = null;
  private url: string;
  private onMessage: (event: SSEEvent) => void;
  private onError: (error: any) => void;
  private onEnd: () => void;

  constructor(
    caseId: string,
    callbacks: {
      onMessage: (event: SSEEvent) => void;
      onError?: (error: any) => void;
      onEnd?: () => void;
    }
  ) {
    const baseUrl = typeof window !== "undefined"
      ? "/api"
      : (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api");
    this.url = `${baseUrl}/investigations/${caseId}/stream`;
    this.onMessage = callbacks.onMessage;
    this.onError = callbacks.onError || console.error;
    this.onEnd = callbacks.onEnd || (() => {});
  }

  connect() {
    if (this.eventSource) {
      this.disconnect();
    }

    this.eventSource = new EventSource(this.url);

    this.eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === "stream_end" || data.type === "timeout") {
          this.onEnd();
          this.disconnect();
        } else if (data.type !== "heartbeat") {
          this.onMessage(data);
        }
      } catch (err) {
        console.error("Failed to parse SSE event", err);
      }
    };

    this.eventSource.onerror = (err) => {
      this.onError(err);
      this.disconnect();
    };
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
