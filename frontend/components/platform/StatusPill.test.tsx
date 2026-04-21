import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusPill } from "./StatusPill";

describe("StatusPill", () => {
  it("renders the status label", () => {
    render(<StatusPill status="deployed" />);
    expect(screen.getByText("deployed")).toBeInTheDocument();
  });
  it("applies pulse only when deployed + livePulse", () => {
    const { container } = render(<StatusPill status="draft" livePulse />);
    expect(container.querySelector(".animate-vaPulse")).toBeNull();
  });
});
