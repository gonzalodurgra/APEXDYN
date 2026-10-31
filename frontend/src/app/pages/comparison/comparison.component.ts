import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Vehicle, Track, TrackVariant, CompareResponse } from '../../models/types';

@Component({
  selector: 'app-comparison',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './comparison.component.html',
  styleUrl: './comparison.component.css'
})
export class ComparisonComponent implements OnInit {
  vehicles: Vehicle[] = [];
  tracks: Track[] = [];
  currentVariants: TrackVariant[] = [];

  selectedTrackId = '';
  selectedVariantId = '';
  selectedVehicleIds: string[] = [];

  isComparing = false;
  overallGap: number = 0;
  selectedTrack: Track | null = null;
  selectedVariant: TrackVariant | null = null;
  errorMessage = '';
  compareResult?: CompareResponse | null;

  gapValues: number[] = [];

  constructor(private api: ApiService) { }

  ngOnInit(): void {
    this.api.getVehicles(1, 100).subscribe({
      next: (res) => {
        this.vehicles = res.items;
        if (this.vehicles.length >= 2) {
          this.selectedVehicleIds = [this.vehicles[0].id, this.vehicles[1].id];
        } else if (this.vehicles.length === 1) {
          this.selectedVehicleIds = [this.vehicles[0].id];
        }
      }
    });

    this.api.getTracks().subscribe({
      next: (res) => {
        this.tracks = res.items;
        if (this.tracks.length > 0) {
          this.selectedTrackId = this.tracks[0].id;
          this.selectedTrack = this.tracks[0];
          this.onTrackChange();
        }
      }
    });
  }

  onTrackChange(): void {
    this.selectedTrack = this.tracks.find(t => t.id === this.selectedTrackId) || null;

    if (!this.selectedTrackId) {
      this.currentVariants = [];
      this.selectedVariantId = '';
      this.selectedVariant = null;
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
          this.selectedVariant = null;
        }
      },
      error: (err) => {
        console.error('Error al cargar variantes para comparativa:', err);
        this.currentVariants = [];
        this.selectedVariantId = '';
        this.selectedVariant = null;
      }
    });
  }

  onVariantChange(): void {
    this.selectedVariant = this.currentVariants.find(v => v.id === this.selectedVariantId) || null;
  }

  isSelected(id: string): boolean {
    return this.selectedVehicleIds.includes(id);
  }

  toggleVehicle(id: string): void {
    if (this.isSelected(id)) {
      this.selectedVehicleIds = this.selectedVehicleIds.filter(vId => vId !== id);
    } else {
      this.selectedVehicleIds.push(id);
    }
  }

  formatTime(s?: number): string {
    if (s === undefined || s === null || isNaN(s)) return '--:--.---';
    const min = Math.floor(s / 60);
    const sec = s % 60;
    return `${min}:${sec < 10 ? '0' : ''}${sec.toFixed(3)}`;
  }

  runComparison(): void {
    if (this.selectedVehicleIds.length < 2 || !this.selectedVariantId) return;

    this.isComparing = true;
    this.errorMessage = '';
    this.compareResult = null;
    this.overallGap = 0;
    this.gapValues = [];

    this.api.compareVehicles(this.selectedVehicleIds, this.selectedVariantId).subscribe({
      next: (res) => {
        console.log(res);
        // Enriquecer información del trazado desde el estado de la vista
        if (!res.track_name && this.selectedTrack) {
          res.track_name = this.selectedTrack.name;
        }
        if (!res.variant_name && this.selectedVariant) {
          res.variant_name = this.selectedVariant.name;
        }
        if (!res.track_length_m && this.selectedVariant) {
          res.track_length_m = this.selectedVariant.length_m;
        }

        this.compareResult = res;

        // Calcular gaps de manera precisa filtrando elementos con error o sin tiempo
        const validTimes = res.results
          .map(r => r.total_time_s)
          .filter((t): t is number => typeof t === 'number' && !isNaN(t) && t > 0);

        if (validTimes.length > 0) {
          const fastest = Math.min(...validTimes);
          this.gapValues = res.results.map(r => {
            if (typeof r.total_time_s === 'number' && !isNaN(r.total_time_s) && r.total_time_s > 0) {
              return +(r.total_time_s - fastest).toFixed(3);
            }
            return 0;
          });
          this.overallGap = +(Math.max(...validTimes) - fastest).toFixed(3);
        } else {
          this.gapValues = res.results.map(() => 0);
          this.overallGap = 0;
        }

        this.isComparing = false;
      },
      error: (err) => {
        this.isComparing = false;
        this.errorMessage = err.error?.detail || 'Error al ejecutar la comparativa física entre vehículos.';
      }
    });
  }
}
