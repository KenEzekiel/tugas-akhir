"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { searchContracts } from "@/lib/actions";
import { ContractDetails } from "@/components/contract-details";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ContractResult } from "@/lib/types";
import { Copy, ExternalLink, FileCode, Tag } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export function ResultsList() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q");
  const threshold = parseFloat(searchParams.get("threshold") || "0.7");
  const { toast } = useToast();

  const [results, setResults] = useState<ContractResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedContract, setSelectedContract] = useState<string | null>(null);
  const [contractDetails, setContractDetails] = useState<ContractResult | null>(
    null
  );
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    async function fetchResults() {
      if (!query) return;

      setLoading(true);
      try {
        const data = await searchContracts(query, 10, threshold);
        console.log(data, "vector search data");
        setResults(data);
      } catch (error) {
        console.error("Error fetching results:", error);
        toast({
          title: "Error",
          description: "Failed to fetch search results. Please try again.",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    }

    fetchResults();
  }, [query, threshold, toast]);

  const handleViewDetails = async (contractId: string) => {
    setSelectedContract(contractId);
    setLoadingDetails(true);

    try {
      const contract = results.find((r) => r.id === contractId);
      if (!contract) {
        throw new Error("Contract not found");
      }

      setContractDetails(contract);
    } catch (error) {
      console.error("Error fetching contract details:", error);
      toast({
        title: "Error",
        description: "Failed to load contract details. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoadingDetails(false);
    }
  };

  if (!query) {
    return (
      <div className="text-center py-12">
        <FileCode className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
          No search query
        </h3>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Enter a search term to find smart contracts
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold mb-4">
          🔍 Vector searching for: "{query}"
        </h2>
        {[1, 2, 3].map((i) => (
          <Card key={`skeleton-${i}`} className="overflow-hidden">
            <CardHeader className="pb-2">
              <Skeleton className="h-6 w-1/3" />
              <Skeleton className="h-4 w-2/3" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-5/6" />
            </CardContent>
            <CardFooter>
              <Skeleton className="h-8 w-24" />
            </CardFooter>
          </Card>
        ))}
      </div>
    );
  }

  if (selectedContract && contractDetails) {
    return (
      <ContractDetails
        contract={contractDetails}
        onBack={() => {
          setSelectedContract(null);
          setContractDetails(null);
        }}
      />
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">
        🔍 {results.length} results for: "{query}"
      </h2>

      {results.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
          <FileCode className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
            No similar contracts found
          </h3>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Try adjusting your search terms
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {results.map((contract) => (
            <Card
              key={`${contract.id}-${contract.name}`}
              className="overflow-hidden hover:shadow-md transition-shadow"
            >
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg">
                      {contract.name || "Unnamed Contract"}
                    </CardTitle>
                    <CardDescription>
                      {contract.description || "No description available"}
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {contract.verified && (
                      <Badge variant="default">Verified</Badge>
                    )}
                    {contract.solc_version && (
                      <Badge variant="outline">
                        Solidity {contract.solc_version}
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2 mb-3">
                  {contract.tags?.map((tag, i) => (
                    <Badge
                      key={`${tag}-${i}`}
                      variant="secondary"
                      className="flex items-center gap-1"
                    >
                      <Tag className="h-3 w-3" />
                      {tag}
                    </Badge>
                  ))}
                  {contract.domain && (
                    <Badge
                      variant="secondary"
                      className="flex items-center gap-1"
                    >
                      <Tag className="h-3 w-3" />
                      {contract.domain}
                    </Badge>
                  )}
                </div>
                {contract.functionality && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                    <p className="font-medium">Functionality:</p>
                    <p>{contract.functionality}</p>
                  </div>
                )}
                {contract.security_risks &&
                  contract.security_risks.length > 0 && (
                    <div className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                      <p className="font-medium">Security Considerations: </p>
                      <p>{contract.security_risks}</p>
                    </div>
                  )}
              </CardContent>
              <CardFooter className="flex flex-wrap gap-2">
                <Button
                  variant="default"
                  onClick={() => handleViewDetails(contract.id)}
                  disabled={loadingDetails && selectedContract === contract.id}
                >
                  {loadingDetails && selectedContract === contract.id ? (
                    <span className="flex items-center gap-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      Loading...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      View Details
                    </span>
                  )}
                </Button>

                {contract.address && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(contract.address!);
                      toast({
                        title: "Address copied",
                        description: "Contract address copied to clipboard",
                      });
                    }}
                    className="flex items-center gap-1"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    Copy Address
                  </Button>
                )}

                {contract.externalUrl && (
                  <Button
                    variant="outline"
                    size="icon"
                    asChild
                    className="ml-auto"
                  >
                    <a
                      href={contract.externalUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <ExternalLink className="h-4 w-4" />
                      <span className="sr-only">External link</span>
                    </a>
                  </Button>
                )}
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
