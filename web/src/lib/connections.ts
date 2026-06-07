export type OverviewWithConnections = {
  configured: boolean;
  connections: Array<{
    status: string;
    toolkit_slug: string;
    is_disabled: boolean;
  }>;
};

export function isToolkitEnabled(
  overview: OverviewWithConnections | null,
  toolkitSlug: string,
): boolean {
  if (!overview?.configured) {
    return false;
  }
  const u = toolkitSlug.toUpperCase();
  return overview.connections.some(
    (c) => c.toolkit_slug.toUpperCase() === u && c.status === "ACTIVE" && !c.is_disabled,
  );
}
