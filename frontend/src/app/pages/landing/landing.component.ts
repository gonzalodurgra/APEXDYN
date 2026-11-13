import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './landing.component.html',
  styleUrls: ['./landing.component.css']
})
export class LandingComponent {
  features = [
    {
      icon: '⚡',
      tag: 'QSS ENGINE V5.0',
      title: 'Simulación Cuasi-Estacionaria (QSS)',
      description: 'Cálculo de envelope dinámico, aceleraciones longitudinales y laterales acopladas con el elipse de adherencia y transferencia de carga en tiempo real.',
      route: '/simulation',
      cta: 'Abrir Simulador'
    },
    {
      icon: '🏎️',
      tag: 'TELEMETRÍA & AERODINÁMICA',
      title: 'Hangar & Catálogo de Vehículos',
      description: 'Explora fichas técnicas detalladas: mapas motor, curvas de potencia/par, coeficientes Cd/Cl, downforce y distribución de pesos.',
      route: '/catalog',
      cta: 'Explorar Catálogo'
    },
    {
      icon: '⚔️',
      tag: 'BENCHMARKING DINÁMICO',
      title: 'Duelo Cara a Cara',
      description: 'Compara dos hiperdeportivos o monoplazas en circuitos clave (Monza, Spa, Nürburgring) con trazado de deltas de tiempo sector por sector.',
      route: '/comparison',
      cta: 'Iniciar Duelo'
    },
    {
      icon: '⏱️',
      tag: 'DEGRADACIÓN & ESTRATEGIA',
      title: 'Simulación de Resistencia',
      description: 'Estrategias de stint, consumo de combustible, ventanas de parada en boxes y degradación térmica de compuestos neumáticos.',
      route: '/endurance',
      cta: 'Calcular Stint'
    }
  ];

  stats = [
    { value: '< 2.5 ms', label: 'Latencia de Cálculo QSS' },
    { value: '99.4%', label: 'Precisión con Telemetría Real' },
    { value: '4+', label: 'Circuitos GP Homologados' },
    { value: '6-DOF', label: 'Modelo Dinámico de Adherencia' }
  ];

  techSpecs = [
    { name: 'Pacejka Magic Formula 5.2', category: 'Neumáticos', status: 'Activo' },
    { name: 'Aero Map 3D (Ride Height & Yaw)', category: 'Aerodinámica', status: 'Activo' },
    { name: 'Multi-Gear Shift Delay & Losses', category: 'Powertrain', status: 'Activo' },
    { name: 'Dynamic Fuel Mass Decay', category: 'Masa & Balance', status: 'Activo' }
  ];
}
