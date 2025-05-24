import * as d3 from 'd3';
import { useEffect, useRef } from 'react';

type RiskGaugeProps = {
  value: number; // 0-1
  width?: number;
  height?: number;
};

export const RiskGauge = ({ value = 0.5, width = 300, height = 200 }: RiskGaugeProps) => {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();

    // Шкала
    const arcGenerator = d3.arc();
    const gaugeArc = arcGenerator({
      innerRadius: 50,
      outerRadius: 80,
      startAngle: -Math.PI * 0.8,
      endAngle: Math.PI * 0.8,
    });

    // Индикатор
    const needleValue = Math.max(0, Math.min(1, value));
    const needleAngle = d3.scaleLinear()
      .domain([0, 1])
      .range([-Math.PI * 0.8, Math.PI * 0.8]);

    svg.append('path')
      .attr('d', gaugeArc)
      .attr('fill', '#eee')
      .attr('transform', `translate(${width/2}, ${height-20})`);

    svg.append('line')
      .attr('x1', width/2)
      .attr('y1', height-20)
      .attr('x2', width/2 + Math.cos(needleAngle(needleValue)) * 70)
      .attr('y2', height-20 + Math.sin(needleAngle(needleValue)) * 70)
      .attr('stroke', '#ff3d00')
      .attr('stroke-width', 3);

    // Метки
    ['Low', 'Medium', 'High'].forEach((label, i) => {
      svg.append('text')
        .text(label)
        .attr('x', width/2 + Math.cos(needleAngle(i * 0.5)) * 100)
        .attr('y', height-20 + Math.sin(needleAngle(i * 0.5)) * 100)
        .attr('text-anchor', 'middle')
        .attr('fill', '#666');
    });
  }, [value]);

  return <svg ref={ref} width={width} height={height} />;
};
