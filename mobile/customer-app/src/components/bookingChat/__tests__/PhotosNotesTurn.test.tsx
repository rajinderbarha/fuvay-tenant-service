import React from "react";
import { act, fireEvent, screen, waitFor } from "@testing-library/react-native";
import * as ImagePicker from "expo-image-picker";

import { renderWithProviders } from "../../../testing/renderWithProviders";
import { PhotosNotesTurn } from "../PhotosNotesTurn";

jest.mock("expo-image-picker", () => ({
  requestMediaLibraryPermissionsAsync: jest.fn(),
  launchImageLibraryAsync: jest.fn(),
}));

describe("PhotosNotesTurn", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders every server attachment as a visible preview", () => {
    renderWithProviders(
      <PhotosNotesTurn
        photoUrls={["https://res.cloudinary.com/fuvay/image/upload/one.jpg", "https://res.cloudinary.com/fuvay/image/upload/two.jpg"]}
        onAddPhoto={async () => {}}
        onRemovePhoto={async () => {}}
        onContinue={() => {}}
      />,
    );

    expect(screen.getAllByLabelText("Photo attached")).toHaveLength(2);
  });

  it("shows the selected device image immediately while Cloudinary attachment is pending", async () => {
    let finishUpload: (() => void) | undefined;
    const upload = new Promise<void>(resolve => { finishUpload = resolve; });
    (ImagePicker.requestMediaLibraryPermissionsAsync as jest.Mock).mockResolvedValue({ granted: true });
    (ImagePicker.launchImageLibraryAsync as jest.Mock).mockResolvedValue({
      canceled: false,
      assets: [{ uri: "file:///customer/ac-problem.jpg", fileName: "ac-problem.jpg", mimeType: "image/jpeg" }],
    });
    const onAddPhoto = jest.fn(() => upload);

    renderWithProviders(
      <PhotosNotesTurn photoUrls={[]} onAddPhoto={onAddPhoto} onRemovePhoto={async () => {}} onContinue={() => {}} />,
    );
    fireEvent.press(screen.getByLabelText("Add a photo"));

    await waitFor(() => expect(screen.getByLabelText("Photo uploading")).toBeTruthy());
    expect(onAddPhoto).toHaveBeenCalledWith({
      uri: "file:///customer/ac-problem.jpg",
      fileName: "ac-problem.jpg",
      mimeType: "image/jpeg",
    });
    await act(async () => {
      finishUpload?.();
      await upload;
    });
    await waitFor(() => expect(screen.queryByLabelText("Photo uploading")).toBeNull());
  });
});
