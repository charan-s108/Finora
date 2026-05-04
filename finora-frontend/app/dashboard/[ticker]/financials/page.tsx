import { notFound } from "next/navigation";
import { getFinancials } from "@/lib/api";
import FinancialsDetailView from "./FinancialsDetailView";

interface Props {
  params: Promise<{ ticker: string }>;
}

export default async function FinancialsPage({ params }: Props) {
  const { ticker } = await params;
  const upper = ticker.toUpperCase();
  const data = await getFinancials(upper);
  if (!data) notFound();
  return <FinancialsDetailView data={data} ticker={upper} />;
}
