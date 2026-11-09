import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Vehicle, Track, TrackVariant, SimulationResponse } from '../../models/types';
import { SpeedProfileChartComponent } from '../../components/speed-profile-chart/speed-profile-chart.component';
import { TrackMapViewerComponent } from '../../components/track-map-viewer/track-map-viewer.component';

@Component({
  selector: 'app-simulation-studio',
  standalone: true,
  imports: [CommonModule, FormsModule, SpeedProfileChartComponent, TrackMapViewerComponent],
  templateUrl: './simulation-studio.component.html',
  styleUrl: './simulation-studio.component.css'
})
export class SimulationStudioComponent implements OnInit {
  vehicles: Vehicle[] = [];
  tracks: Track[] = [];
  currentVariants: TrackVariant[] = [];
  activeVariant: TrackVariant | null = null;

  // Paginación y filtro de vehículos
  vehicleSearchQuery = '';
  currentPage = 1;
  pageSize = 12;
  totalVehicles = 0;
  totalPages = 1;
  loadingVehicles = false;

  selectedVehicleId = '';
  selectedTrackId = '';
  selectedVariantId = '';
  initialSpeedKmh = 0;

  isSimulating = false;
  simResult: SimulationResponse | null = null;
  errorMessage = '';

  constructor(private api: ApiService) { }

  ngOnInit(): void {
    this.loadVehicles();
    this.loadTracks();
  }

  loadVehicles(page: number = this.currentPage): void {
    this.currentPage = page;
    this.loadingVehicles = true;
    this.api.getVehicles(this.currentPage, this.pageSize, this.vehicleSearchQuery).subscribe({
      next: (res) => {
        this.vehicles = res.items || [];
        this.totalVehicles = res.total;
        this.totalPages = res.pages || Math.ceil(res.total / this.pageSize) || 1;
        if (this.vehicles.length > 0) {
          const exists = this.vehicles.some(v => v.id === this.selectedVehicleId);
          if (!exists) {
            this.selectedVehicleId = this.vehicles[0].id;
          }
        }
        this.loadingVehicles = false;
      },
      error: () => {
        this.loadingVehicles = false;
      }
    });
  }

  loadTracks(): void {
    this.api.getTracks().subscribe({
      next: (res) => {
        this.tracks = res.items;
        if (this.tracks.length > 0) {
          this.selectedTrackId = this.tracks[0].id;
          this.onTrackChange();
        }
      }
    });
  }

  goToVehiclePage(page: number): void {
    if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
      this.loadVehicles(page);
    }
  }

  onVehicleSearchChange(): void {
    this.currentPage = 1;
    this.loadVehicles(1);
  }

  onVehicleChange(): void {
    const vehicle = this.vehicles.find(v => v.id === this.selectedVehicleId);
    if (vehicle) {
      this.selectedVehicleId = vehicle.id;
    }
  }

  onTrackChange(): void {
    if (!this.selectedTrackId) {
      this.currentVariants = [];
      this.selectedVariantId = '';
      this.activeVariant = null;
      return;
    }

    this.api.getTrackVariants(this.selectedTrackId).subscribe({
      next: (res) => {
        this.currentVariants = res.items || [];
        if (this.currentVariants.length > 0) {
          this.selectedVariantId = this.currentVariants[0].id;
          this.onVariantChange();
        } else {
          this.selectedVariantId = '';
          this.activeVariant = null;
        }
      },
      error: (err) => {
        console.error('Error al cargar variantes:', err);
        this.currentVariants = [];
        this.selectedVariantId = '';
        this.activeVariant = null;
      }
    });
  }

  onVariantChange(): void {
    this.activeVariant = this.currentVariants.find(v => v.id === this.selectedVariantId) || null;
  }

  runSingleSimulation(): void {
    if (!this.selectedVehicleId || !this.selectedVariantId) return;

    this.isSimulating = true;
    this.errorMessage = '';
    this.simResult = null;

    this.api.runSimulation(this.selectedVehicleId, this.selectedVariantId, this.initialSpeedKmh).subscribe({
      next: (res) => {
        this.simResult = res;
        this.isSimulating = false;
        console.log(this.simResult)
      },
      error: (err) => {
        this.isSimulating = false;
        this.errorMessage = err.error?.detail || 'Error al ejecutar la simulación física.';
      }
    });
  }

  formatTime(s: number): string {
    const min = Math.floor(s / 60);
    const sec = s % 60;
    return `${min}:${sec < 10 ? '0' : ''}${sec.toFixed(3)}`;
  }
}
