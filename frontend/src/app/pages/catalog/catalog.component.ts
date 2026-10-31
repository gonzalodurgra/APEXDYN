import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Vehicle } from '../../models/types';
import { EngineCurveChartComponent } from '../../components/engine-curve-chart/engine-curve-chart.component';

@Component({
  selector: 'app-catalog',
  standalone: true,
  imports: [CommonModule, FormsModule, EngineCurveChartComponent],
  templateUrl: './catalog.component.html',
  styleUrl: './catalog.component.css'
})
export class CatalogComponent implements OnInit {
  vehicles: Vehicle[] = [];
  selectedVehicle: Vehicle | null = null;
  loading = false;
  searchQuery = '';
  selectedDrivetrain = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadVehicles();
  }

  loadVehicles(): void {
    this.loading = true;
    this.api.getVehicles(1, 50, this.searchQuery, this.selectedDrivetrain).subscribe({
      next: (res) => {
        this.vehicles = res.items;
        if (this.vehicles.length > 0 && !this.selectedVehicle) {
          this.selectVehicle(this.vehicles[0]);
        }
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  selectVehicle(v: Vehicle): void {
    // Cargar con subsistemas completos
    this.api.getVehicle(v.id).subscribe({
      next: (full) => {
        this.selectedVehicle = full;
      },
      error: () => {
        this.selectedVehicle = v;
      }
    });
  }

  onSearchChange(): void {
    this.loadVehicles();
  }
}
