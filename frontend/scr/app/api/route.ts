import { NextResponse } from 'next/server';
import { fetchRiskData } from '@/lib/api/backend';

export async function GET() {
  const data = await fetchRiskData();
  return NextResponse.json(data);
}
