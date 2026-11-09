import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
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
  @ViewChild('chartSection') chartSection!: ElementRef;

  // existing properties
  vehicles: Vehicle[] = [];
  selectedVehicle: Vehicle | null = null;
  loading = false;
  searchQuery = '';
  selectedDrivetrain = '';

  // Paginación
  currentPage = 1;
  pageSize = 12;
  totalVehicles = 0;
  totalPages = 1;

  constructor(private api: ApiService) { }

  ngOnInit(): void {
    this.loadVehicles();
  }

  loadVehicles(page: number = this.currentPage): void {
    this.currentPage = page;
    this.loading = true;
    this.api.getVehicles(this.currentPage, this.pageSize, this.searchQuery, this.selectedDrivetrain).subscribe({
      next: (res) => {
        this.vehicles = res.items;
        this.totalVehicles = res.total;
        this.totalPages = res.pages || Math.ceil(res.total / this.pageSize) || 1;
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

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
      this.loadVehicles(page);
    }
  }

  selectVehicle(v: Vehicle): void {
    // Cargar con subsistemas completos
    this.api.getVehicle(v.id).subscribe({
      next: (full) => {
        this.selectedVehicle = full;
        // Después de cargar, desplazar a la sección del gráfico en dispositivos móviles
        if (this.chartSection) {
          this.chartSection.nativeElement.scrollIntoView();
        };
      },
      error: () => {
        this.selectedVehicle = v;
        if (this.chartSection) {
          this.chartSection.nativeElement.scrollIntoView();
        };
      }
    });
  }

  onSearchChange(): void {
    this.currentPage = 1;
    this.loadVehicles(1);
  }

  onDrivetrainChange(): void {
    this.currentPage = 1;
    this.loadVehicles(1);
  }
}
