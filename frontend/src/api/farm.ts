import { listProductionUnits, type ProductionUnit } from './productionUnits'
import { listScenarios, type Scenario } from './scenarios'
import { listScenarioWaterPoints, type ScenarioWaterPoint } from './waterPoints'

// Lo que muestran las pantallas de Mi campo: el escenario, sus sectores y sus aguadas
export interface ScenarioMap {
  scenario: Scenario
  units: ProductionUnit[]
  waterPoints: ScenarioWaterPoint[]
}

// Devuelve null si el escenario no existe o no es del usuario
export async function loadScenarioMap(scenarioId: number): Promise<ScenarioMap | null> {
  const scenario = (await listScenarios()).find((item) => item.id === scenarioId)
  if (!scenario) return null
  const [units, waterPoints] = await Promise.all([
    listProductionUnits(scenarioId),
    listScenarioWaterPoints(scenarioId),
  ])
  return { scenario, units, waterPoints }
}
