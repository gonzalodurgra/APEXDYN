import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Vehicle, Track, TrackVariant, EnduranceResult } from '../../models/types';

@Component({
  selector: 'app-endurance',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './endurance.component.html',
  styleUrls: ['./endurance.component.css']
})
export class EnduranceComponent implements OnInit {
  vehicles: Vehicle[] = [];
  tracks: Track[] = [];
  selectedVehicleId = '';
  selectedTrackId = '';
  variants: TrackVariant[] = [];
  selectedVariantId = '';

  // Formulario de Carrera
  raceMode: 'laps' | 'hours' | 'distance' = 'laps';
  raceLaps = 20;
  raceDurationHours = 2.0;
  raceDistanceKm = 100.0;
  ambientTempC = 25.0;
  bsfcGkwh = 260.0;
  initialFuelL = 100.0;
  powerMode = 1.0;
  driverAggression = 1.0;
  randomSeed = 42;

  // Estrategia
  tankCapacityL = 100.0;
  fuelFillRateLs = 2.5;
  tireChangeTimeS = 14.0;
  brakeServiceTimeS = 120.0;
  pitLaneDeltaS = 22.0;
  minFuelReserveL = 5.0;
  tireWearThreshold = 0.75;
  brakeWearThreshold = 0.80;
  repairOnPit = true;

  // Estado de simulación
  loading = false;
  errorMessage = '';
  result: EnduranceResult | null = null;
  componentKeys: string[] = [];

  constructor(private apiService: ApiService) { }

  ngOnInit(): void {
    this.loadCatalog();
  }

  loadCatalog(): void {
    this.apiService.getVehicles(1, 100).subscribe({
      next: (res) => {
        this.vehicles = res.items || [];
        if (this.vehicles.length > 0) {
          this.selectedVehicleId = this.vehicles[0].id;
        }
      },
      error: (err) => console.error('Error cargando vehículos:', err)
    });

    this.apiService.getTracks().subscribe({
      next: (res) => {
        this.tracks = res.items || [];
        if (this.tracks.length > 0) {
          this.selectedTrackId = this.tracks[0].id;
          this.onTrackChange();
        }
      },
      error: (err) => console.error('Error cargando trazados:', err)
    });
  }

  onTrackChange(): void {
    if (!this.selectedTrackId) return;
    this.apiService.getTrackVariants(this.selectedTrackId).subscribe({
      next: (res) => {
        this.variants = res.items || [];
        if (this.variants.length > 0) {
          this.selectedVariantId = this.variants[0].id;
        } else {
          this.selectedVariantId = '';
        }
      },
      error: (err) => console.error('Error cargando variantes:', err)
    });
  }

  runSimulation(): void {
    if (!this.selectedVehicleId || !this.selectedVariantId) {
      this.errorMessage = 'Selecciona un vehículo y una variante de trazado válidos.';
      return;
    }

    this.loading = true;
    this.errorMessage = '';
    this.result = null;

    const payload: any = {
      vehicle_id: this.selectedVehicleId,
      variant_id: this.selectedVariantId,
      ambient_temp_c: this.ambientTempC,
      bsfc_g_kwh: this.bsfcGkwh,
      initial_fuel_l: this.initialFuelL,
      power_mode: this.powerMode,
      driver_aggression: this.driverAggression,
      random_seed: this.randomSeed,
      strategy: {
        tank_capacity_l: this.tankCapacityL,
        fuel_fill_rate_l_s: this.fuelFillRateLs,
        tire_change_time_s: this.tireChangeTimeS,
        brake_service_time_s: this.brakeServiceTimeS,
        pit_lane_delta_s: this.pitLaneDeltaS,
        min_fuel_reserve_l: this.minFuelReserveL,
        tire_wear_threshold: this.tireWearThreshold,
        brake_wear_threshold: this.brakeWearThreshold,
        repair_on_pit: this.repairOnPit,
        force_pit_laps: []
      }
    };

    if (this.raceMode === 'laps') {
      payload.race_laps = this.raceLaps;
    } else if (this.raceMode === 'hours') {
      payload.race_duration_hours = this.raceDurationHours;
    } else if (this.raceMode === 'distance') {
      payload.race_distance_km = this.raceDistanceKm;
    }

    this.apiService.runEnduranceSimulation(payload).subscribe({
      next: (res: EnduranceResult) => {
        this.result = res;
        this.componentKeys = Object.keys(res.components || {});
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Error al ejecutar la simulación de resistencia.';
        this.loading = false;
      }
    });
  }

  formatTime(seconds: number): string {
    if (!seconds || seconds <= 0) return '0:00.000';
    const totalSecs = Math.floor(seconds);
    const ms = Math.floor((seconds - totalSecs) * 1000);
    const hours = Math.floor(totalSecs / 3600);
    const mins = Math.floor((totalSecs % 3600) / 60);
    const secs = totalSecs % 60;

    const msStr = ms.toString().padStart(3, '0');
    const secsStr = secs.toString().padStart(2, '0');

    if (hours > 0) {
      const minsStr = mins.toString().padStart(2, '0');
      return `${hours}:${minsStr}:${secsStr}.${msStr}`;
    }

    return `${mins}:${secsStr}.${msStr}`;
  }
}

