import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EvidenceGallery } from "../EvidenceGallery";
import { FIXTURE_MEDIA_ASSETS } from "../../../lib/ux03/fixtures";

describe("EvidenceGallery — no storage keys/signed URLs/credentials leak", () => {
  it("renders label/kind/size/date but never a previewToken value", () => {
    render(<EvidenceGallery assets={FIXTURE_MEDIA_ASSETS} />);
    expect(screen.getByText(FIXTURE_MEDIA_ASSETS[0].label)).toBeInTheDocument();
    for (const asset of FIXTURE_MEDIA_ASSETS) {
      expect(screen.queryByText(asset.previewToken)).not.toBeInTheDocument();
    }
  });

  it("renders an empty state, not an error, when there are no assets", () => {
    render(<EvidenceGallery assets={[]} />);
    expect(screen.getByText(/no media attached/i)).toBeInTheDocument();
  });
});
