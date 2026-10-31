import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  Vehicle,
  PaginatedResponse,
  Manufacturer,
  Track,
  SimulationResponse,
  CompareResponse,
  TrackVariant
} from '../models/types';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly baseUrl = 'http://localhost:8000/api/v1';

  constructor(private http: HttpClient) { }

  // Fabricantes
  getManufacturers(): Observable<PaginatedResponse<Manufacturer>> {
    return this.http.get<PaginatedResponse<Manufacturer>>(`${this.baseUrl}/manufacturers?size=100`);
  }

  // Vehículos
  getVehicles(page = 1, size = 20, search?: string, drivetrain?: string): Observable<PaginatedResponse<Vehicle>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('size', size.toString());

    if (search) params = params.set('search', search);
    if (drivetrain) params = params.set('drive_type', drivetrain);
    this.http.get<PaginatedResponse<Vehicle>>(`${this.baseUrl}/vehicles`, { params }).subscribe(
      response => console.log(response)
    )

    return this.http.get<PaginatedResponse<Vehicle>>(`${this.baseUrl}/vehicles`, { params });
  }

  getVehicle(id: string): Observable<Vehicle> {
    return this.http.get<Vehicle>(`${this.baseUrl}/vehicles/${id}`);
  }

  // Circuitos
  getTracks(): Observable<PaginatedResponse<Track>> {
    return this.http.get<PaginatedResponse<Track>>(`${this.baseUrl}/tracks?size=100`);
  }

  getTrack(id: string): Observable<Track> {
    return this.http.get<Track>(`${this.baseUrl}/tracks/${id}`);
  }

  getTrackVariants(trackId: string): Observable<PaginatedResponse<TrackVariant>> {
    return this.http.get<PaginatedResponse<TrackVariant>>(`${this.baseUrl}/tracks/${trackId}/variants`);
  }

  getTrackVariant(variantId: string): Observable<TrackVariant> {
    return this.http.get<TrackVariant>(`${this.baseUrl}/tracks/variants/${variantId}`);
  }

  // Simulaciones Físicas QSS
  runSimulation(vehicleId: string, trackVariantId: string, initialSpeedKmh = 0.0, stepSizeM = 2.0): Observable<SimulationResponse> {
    // Adaptado al esquema SimulationRequest del backend
    return this.http.post<SimulationResponse>(`${this.baseUrl}/simulations`, {
      vehicle_id: vehicleId,
      variant_id: trackVariantId,
      initial_speed_kmh: initialSpeedKmh,
      // Opcionales con valores por defecto; se pueden omitir pero se incluyen explícitamente
      driver_profile_id: null,
      condition_id: null,
      simulation_mode: "vehicle_limit",
      surface_wetness: null,
      tire_mu_override: null,
      num_sectors: 3,

    });
  }

  compareVehicles(vehicleIds: string[], trackVariantId: string): Observable<CompareResponse> {
    // Adaptado al esquema CompareRequest del backend
    return this.http.post<CompareResponse>(`${this.baseUrl}/simulations/compare`, {
      vehicle_ids: vehicleIds,
      variant_id: trackVariantId,
      // Opcionales con valores por defecto
      surface_wetness: null,
      num_sectors: 3,

    });
  }

  getSimulationHistory(variantId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/simulations/history/${variantId}`);
  }
}
