import QtQuick 2.4
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.4
import org.kde.kirigami 2.4 as Kirigami
import Mycroft 1.0 as Mycroft

Mycroft.CardDelegate {
    id: root
    height: parent.height
    cardBackgroundOverlayColor: "black"

    Title {
            id: articleTitle
            anchors.top: parent.top
            fontSize: gridUnit * 3
            fontStyle: "Bold"
            heightUnits: 3
            text: sessionData.title
        }

    Image {
        id: featureImage
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: articleTitle.bottom
        anchors.topMargin: gridUnit * 2
        anchors.bottomMargin: gridUnit
        fillMode: Image.PreserveAspectFit
        source: sessionData.imgLink
    }
}
