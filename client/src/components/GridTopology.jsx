import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function GridTopology({ observation }) {
  const svgRef = useRef();

  useEffect(() => {
    if (!observation?.grid_topology) return;

    const { buses, lines } = observation.grid_topology;
    const faults           = observation.identified_faults ?? [];
    const scada            = observation.scada_readings ?? {};

    const faultIds = new Set(faults.map(f => f.component_id));
    const tripped  = new Set(lines.filter(l => l.status === 'TRIPPED').map(l => l.id));
    const blacked  = new Set(buses.filter(b => b.status === 'DE-ENERGISED').map(b => b.id));

    const W = svgRef.current.clientWidth || 700;
    const H = 420;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('width', W).attr('height', H);

    const nodes = buses.map(b => ({ ...b, id: b.id }));
    const edges = lines.map(l => ({ ...l, source: l.from, target: l.to }));

    const simulation = d3.forceSimulation(nodes)
      .force('link',   d3.forceLink(edges).id(d => d.id).distance(70))
      .force('charge', d3.forceManyBody().strength(-250))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide(28));

    const link = svg.append('g').selectAll('line')
      .data(edges).join('line')
      .attr('stroke',       d => tripped.has(d.id) ? '#ef4444' : '#94a3b8')
      .attr('stroke-width', d => tripped.has(d.id) ? 3 : 1.5)
      .attr('stroke-dasharray', d => tripped.has(d.id) ? '6 3' : null);

    const node = svg.append('g').selectAll('g')
      .data(nodes).join('g')
      .attr('cursor', 'pointer')
      .call(d3.drag()
        .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag',  (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end',   (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
      );

    node.append('circle')
      .attr('r', 14)
      .attr('fill', d => {
        if (faultIds.has(d.id)) return '#f59e0b';
        if (blacked.has(d.id))  return '#ef4444';
        return d.voltage_kv >= 100 ? '#3b82f6' : '#22c55e';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', 9)
      .attr('fill', '#fff')
      .attr('font-weight', 600)
      .text(d => d.id.replace('BUS_', ''));

    node.append('title').text(d => {
      const s = scada[d.id];
      return `${d.id} | ${d.voltage_kv}kV | ${d.status}${s ? ` | V=${s.voltage_pu}pu` : ''}`;
    });

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [observation]);

  const legend = [
    { color: '#3b82f6', label: 'Energised (HV)' },
    { color: '#22c55e', label: 'Energised (MV)' },
    { color: '#ef4444', label: 'De-energised'   },
    { color: '#f59e0b', label: 'Fault found'    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap' }}>
        {legend.map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: '#666' }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: color }} />
            {label}
          </div>
        ))}
        <div style={{ fontSize: 11, color: '#888', marginLeft: 'auto' }}>
          Dashed red line = tripped &nbsp;|&nbsp; Drag nodes to rearrange
        </div>
      </div>
      {observation
        ? <svg ref={svgRef} style={{ width: '100%', display: 'block' }} />
        : <div style={{ height: 420, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa', fontSize: 13 }}>
            Reset an episode to see the grid topology
          </div>
      }
    </div>
  );
}