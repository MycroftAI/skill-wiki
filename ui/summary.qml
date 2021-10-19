import QtQuick 2.4
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.4
import org.kde.kirigami 2.4 as Kirigami
import Mycroft 1.0 as Mycroft

Mycroft.CardDelegate {
    id: root
    cardBackgroundOverlayColor: "black"

    Mycroft.AutoFitLabel {
        id: articleSummary
        anchors.fill: parent
        wrapMode: Text.Wrap
        font.family: "Noto Sans"
        color: "#FFFFFF"
        text: sessionData.summary
    }
}
