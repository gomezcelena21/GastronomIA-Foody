// Rubros que Foody entiende (mismos códigos que backend/diseno.py → RUBROS).
export const RUBROS: [string, string][] = [
  ['pasteleria', 'Pastelería y dulces'], ['panaderia', 'Panadería'], ['heladeria', 'Heladería'], ['cafe', 'Café'],
  ['pizzeria', 'Pizzería'], ['parrilla', 'Parrilla'], ['hamburguesa', 'Hamburguesas'], ['sandwicheria', 'Sándwiches'],
  ['empanadas', 'Empanadas'], ['italiana', 'Comida italiana'], ['japonesa', 'Comida japonesa / sushi'],
  ['mexicana', 'Comida mexicana'], ['comida_casera', 'Comida casera / viandas'],
  ['saludable', 'Saludable (vegetariano / vegano)'], ['otra', 'Otro rubro gastronómico'],
]
export const nombreRubro = (codigo: string): string => RUBROS.find(r => r[0] === codigo)?.[1] ?? codigo
