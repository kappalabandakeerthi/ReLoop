const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiRequest<T>(
  path: string,
  token?: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  if (
  options.body &&
  !(typeof FormData !== "undefined" && options.body instanceof FormData) &&
  !headers.has("Content-Type")
) {
  headers.set("Content-Type", "application/json");
}
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Unable to reach the ReLoop API. Check that the backend is running.", 0);
  }

  const text = await response.text();
  let payload: unknown;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = text;
  }

  if (!response.ok) {
    const detail = payload && typeof payload === "object" && "detail" in payload
      ? (payload as { detail: unknown }).detail
      : null;
    const message = Array.isArray(detail)
      ? detail.map((item) => typeof item === "object" && item && "msg" in item
        ? String((item as { msg: unknown }).msg)
        : "Invalid input").join("; ")
      : typeof detail === "string" ? detail : "The request could not be completed.";
    throw new ApiError(message, response.status);
  }

  return payload as T;
}
