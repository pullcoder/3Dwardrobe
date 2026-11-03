import { request } from "./garments";
import type {
  FittingInput,
  FittingResource,
  FittingState,
} from "../types/fitting";

export async function getFittingResource(
  token: string,
  id: string,
  signal?: AbortSignal,
): Promise<FittingResource> {
  return (await request(`/fittings/resources/${id}`, token, { signal })).json();
}
export async function persistFitting(
  token: string,
  body: FittingInput,
  existing?: { id: string; revision: number },
): Promise<FittingState> {
  return (
    await request(existing ? `/fittings/${existing.id}` : "/fittings", token, {
      method: existing ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(
        existing ? { ...body, revision: existing.revision } : body,
      ),
    })
  ).json();
}
export async function getFitting(
  token: string,
  id: string,
): Promise<FittingState> {
  return (await request(`/fittings/${id}`, token)).json();
}
export async function saveOutfit(
  token: string,
  fitting_id: string,
  name: string,
): Promise<FittingState> {
  return (
    await request("/outfits", token, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fitting_id, name }),
    })
  ).json();
}
export async function getOutfits(token: string): Promise<FittingState[]> {
  return (await request("/outfits", token)).json();
}
export async function getOutfit(
  token: string,
  id: string,
): Promise<FittingState> {
  return (await request(`/outfits/${id}`, token)).json();
}
export async function deleteOutfit(token: string, id: string) {
  await request(`/outfits/${id}`, token, { method: "DELETE" });
}
