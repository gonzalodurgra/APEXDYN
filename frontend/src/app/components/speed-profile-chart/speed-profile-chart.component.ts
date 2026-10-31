import { Component, ElementRef, Input, OnChanges, SimpleChanges, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

Chart.register(...registerables);

/** Estructura {d, v} que devuelve el backend en speed_profile, accel_profile, etc. */
export interface ApiProfilePoint {
  d: number;
  v: number;
}

@Component({
  selector: 'app-speed-profile-chart',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './speed-profile-chart.component.html',
  styleUrl: './speed-profile-chart.component.css'
})
export class SpeedProfileChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;

  /** Perfil de velocidad (km/h) vs distancia (m) — formato backend {d, v} */
  @Input() speedProfile: ApiProfilePoint[] = [];
  /** Perfil de aceleración longitudinal (g) vs distancia (m) */
  @Input() accelProfile: ApiProfilePoint[] = [];
  /** Perfil de marcha vs distancia (m) */
  @Input() gearProfile: ApiProfilePoint[] = [];

  public chart: Chart | null = null;

  ngAfterViewInit(): void {
    this.createOrUpdateChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (this.chartCanvas && (changes['speedProfile'] || changes['accelProfile'] || changes['gearProfile'])) {
      this.createOrUpdateChart();
    }
  }

  ngOnDestroy(): void {
    if (this.chart) {
      this.chart.destroy();
    }
  }

  private createOrUpdateChart(): void {
    if (!this.chartCanvas || !this.speedProfile || this.speedProfile.length === 0) return;
    if (this.chart) {
      this.chart.destroy();
    }

    // Los perfiles ya vienen submuestreados desde el backend (máx 500 pts)
    const distances = this.speedProfile.map(p => `${p.d.toFixed(0)}m`);
    const speeds = this.speedProfile.map(p => +p.v.toFixed(1));

    // Interpolar accel_profile a los mismos puntos de distancia que speed_profile
    const longGs = this._interpolateToDistances(
      this.accelProfile,
      this.speedProfile.map(p => p.d)
    );

    const config: ChartConfiguration = {
      type: 'line',
      data: {
        labels: distances,
        datasets: [
          {
            label: 'Velocidad (km/h)',
            data: speeds,
            borderColor: '#00d2ff',
            backgroundColor: 'rgba(0, 210, 255, 0.08)',
            borderWidth: 2,
            fill: true,
            tension: 0.2,
            yAxisID: 'ySpeed',
            pointRadius: 0,
            pointHoverRadius: 4,
          },
          {
            label: 'G Longitudinal',
            data: longGs,
            borderColor: '#10b981',
            borderWidth: 1.5,
            fill: false,
            tension: 0.2,
            yAxisID: 'yG',
            pointRadius: 0,
            pointHoverRadius: 4,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(11, 15, 23, 0.95)',
            borderColor: 'rgba(255, 255, 255, 0.15)',
            borderWidth: 1,
            titleFont: { family: 'JetBrains Mono', size: 12 },
            bodyFont: { family: 'Inter', size: 12 },
            padding: 10
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: {
              color: '#94a3b8',
              maxTicksLimit: 10,
              font: { family: 'JetBrains Mono', size: 10 }
            }
          },
          ySpeed: {
            type: 'linear',
            position: 'left',
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              color: '#00d2ff',
              font: { family: 'JetBrains Mono', size: 10 },
              callback: (val) => `${val} km/h`
            }
          },
          yG: {
            type: 'linear',
            position: 'right',
            grid: { display: false },
            ticks: {
              color: '#a855f7',
              font: { family: 'JetBrains Mono', size: 10 },
              callback: (val) => `${Number(val).toFixed(2)} G`
            }
          }
        }
      }
    };

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (ctx) {
      this.chart = new Chart(ctx, config);
    }
  }

  /**
   * Interpola linealmente un perfil {d,v} a un conjunto de distancias objetivo.
   * Si el perfil está vacío, devuelve array de ceros.
   */
  private _interpolateToDistances(profile: ApiProfilePoint[], targetDs: number[]): number[] {
    if (!profile || profile.length === 0) return targetDs.map(() => 0);
    return targetDs.map(d => {
      // Encontrar el segmento que rodea d
      let lo = 0, hi = profile.length - 1;
      if (d <= profile[lo].d) return +profile[lo].v.toFixed(3);
      if (d >= profile[hi].d) return +profile[hi].v.toFixed(3);
      while (hi - lo > 1) {
        const mid = (lo + hi) >> 1;
        if (profile[mid].d <= d) lo = mid; else hi = mid;
      }
      const t = (d - profile[lo].d) / (profile[hi].d - profile[lo].d);
      return +((1 - t) * profile[lo].v + t * profile[hi].v).toFixed(3);
    });
  }
}
