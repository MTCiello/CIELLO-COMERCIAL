/**
 * A sala do Gerente é fechada (porta de carvalho): parado, o Gerente passeia só por ela, para ser fácil de achar, e os
 * outros agentes não entram nela nem nos Arquivos (que só têm entrada pela sala do Gerente).
 *
 * Run with: npm test
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { test } from 'vitest';

import { OfficeState } from '../src/office/engine/officeState.js';
import type { Character, OfficeLayout } from '../src/office/types.js';
import { Direction } from '../src/office/types.js';

const layout = JSON.parse(
  readFileSync(new URL('../../../central/escritorio/layout-padrao.json', import.meta.url), 'utf-8'),
) as OfficeLayout;

function destinos(directoryName: string, vezes = 200): Array<string | null> {
  const office = new OfficeState(layout);
  office.areaMappings = { Gerente: ['Gerente'], SDR: ['Vendas'] };
  const ch = { id: 1, directoryName, isSubagent: false, conversaCom: null } as unknown as Character;
  const destino = (office as unknown as { destinoParado(c: Character): { col: number; row: number } | null })
    .destinoParado.bind(office);
  return Array.from({ length: vezes }, () => {
    const t = destino(ch);
    return t ? (layout.areaTiles?.[t.row * layout.cols + t.col] ?? null) : 'sem destino';
  });
}

test('o Gerente parado só anda dentro da sala dele', () => {
  assert.deepEqual(new Set(destinos('Gerente')), new Set(['Gerente']));
});

test('os outros agentes não passeiam pela sala do Gerente nem pelos Arquivos', () => {
  const vistos = destinos('SDR');
  assert.ok(!vistos.includes('Gerente'));
  assert.ok(!vistos.includes('Arquivos G'));
  assert.ok(!vistos.includes('sem destino'));
});

/** Os testes não carregam o catálogo de móveis: os lugares entram à mão, 3 por sala, no chão de cada uma. */
function escritorioComLugares(): OfficeState {
  const office = new OfficeState(layout);
  const tiles = layout.areaTiles ?? [];
  const porSala = new Map<string, number>();
  office.seats = new Map();
  for (const w of office.walkableTiles) {
    const sala = tiles[w.row * layout.cols + w.col];
    if (!sala || (porSala.get(sala) ?? 0) >= 3) continue;
    porSala.set(sala, (porSala.get(sala) ?? 0) + 1);
    const uid = `${sala}-${w.col}-${w.row}`;
    office.seats.set(uid, { uid, seatCol: w.col, seatRow: w.row, facingDir: Direction.DOWN, assigned: false });
  }
  return office;
}

function zonaDoLugar(office: OfficeState, id: number): string | null {
  const ch = office.characters.get(id);
  return ch?.seatId ? office.seatZone(ch.seatId) : null;
}

test('ninguém além do Gerente ganha lugar na sala dele, mesmo com o escritório lotado', () => {
  const office = escritorioComLugares();
  office.areaMappings = { Gerente: ['Gerente'], SDR: ['Vendas'] };
  const lugaresDoGerente = [...office.seats.keys()].filter((uid) => office.seatZone(uid) === 'Gerente');
  assert.ok(lugaresDoGerente.length > 0);
  // mais gente do que lugar: a Vendas enche, depois o resto do escritório
  for (let i = 1; i <= office.seats.size + 5; i++) {
    office.addAgent(i, 0, 0, lugaresDoGerente[0], true, i % 2 ? 'SDR' : undefined);
  }
  for (let i = 1; i <= office.seats.size + 5; i++) {
    const zona = zonaDoLugar(office, i);
    assert.ok(zona !== 'Gerente' && zona !== 'Arquivos G', `agente ${i} sentou em ${zona}`);
  }
  office.addAgent(999, 0, 0, undefined, true, 'Gerente');
  assert.equal(zonaDoLugar(office, 999), 'Gerente');
});

test('quem já estava sentado na sala do Gerente sai dela quando as áreas chegam', () => {
  const office = escritorioComLugares();
  const lugarDoGerente = [...office.seats.keys()].find((uid) => office.seatZone(uid) === 'Gerente')!;
  office.addAgent(1, 0, 0, undefined, true, 'Closer');
  office.reassignSeat(1, lugarDoGerente); // como ficava antes: um lugar qualquer, até na sala do Gerente
  assert.equal(zonaDoLugar(office, 1), 'Gerente');
  // a Vendas está lotada: mesmo assim ele sai da sala do Gerente (para outra sala qualquer)
  office.areaMappings = { Gerente: ['Gerente'], Closer: ['Vendas'], SDR: ['Vendas'] };
  for (let i = 2; i <= 4; i++) office.addAgent(i, 0, 0, undefined, true, 'SDR');
  office.setAreaMappings({ Gerente: ['Gerente'], Closer: ['Vendas'], SDR: ['Vendas'] });
  const zona = zonaDoLugar(office, 1);
  assert.ok(zona !== null && zona !== 'Gerente' && zona !== 'Arquivos G', `ficou em ${zona}`);
});
